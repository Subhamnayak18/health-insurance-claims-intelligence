from pathlib import Path
from decimal import Decimal

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyodbc


# ============================================================
# CONFIGURATION
# ============================================================

SOURCE_FILE = Path(
    "data/processed/synthetic/claim_operations.parquet"
)

SERVER = "localhost"
DATABASE = "HealthInsuranceClaimsDW"

BATCH_SIZE = 5_000
EXPECTED_ROWS = 514_225

# Your data is already loaded.
# Keep False to validate the existing SQL table.
# Change to True only when you want to truncate and reload everything.
LOAD_DATA = False


COLUMNS = [
    "CLAIM_KEY",
    "CLAIM_ID",
    "CLAIM_TYPE",
    "BENE_ID",
    "POLICY_ID",
    "PLAN_ID",
    "PRIMARY_PROVIDER_ID",
    "CLAIM_FROM_DATE",
    "CLAIM_THRU_DATE",
    "SUBMISSION_DATE",
    "DECISION_DATE",
    "PAYMENT_DATE",
    "CLAIM_STATUS",
    "DENIAL_REASON",
    "PAYMENT_STATUS",
    "DOCUMENTS_COMPLETE_FLAG",
    "POLICY_ACTIVE_FLAG",
    "TREATMENT_COVERED_FLAG",
    "WAITING_PERIOD_FLAG",
    "PREAUTH_REQUIRED_FLAG",
    "PREAUTH_STATUS",
    "BILLED_AMOUNT",
    "ELIGIBLE_AMOUNT",
    "DEDUCTIBLE_AMOUNT",
    "COPAY_AMOUNT",
    "NON_PAYABLE_AMOUNT",
    "ADJUSTMENT_AMOUNT",
    "APPROVED_AMOUNT",
    "PAID_AMOUNT",
    "SOURCE_CMS_PAYMENT_AMOUNT",
    "TURNAROUND_DAYS",
    "SLA_TARGET_DAYS",
    "SLA_BREACH_FLAG",
    "MANUAL_REVIEW_FLAG",
    "DUPLICATE_INDICATOR",
    "HIGH_COST_FLAG",
    "PROVIDER_RISK_SCORE",
    "FRAUD_ALERT_FLAG",
    "ESTIMATED_LEAKAGE_AMOUNT",
    "REVIEW_PRIORITY",
    "QUEUE_NAME",
    "ADJUSTER_ID",
    "ANALYSIS_DATE",
    "DATA_PROVENANCE",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_value(value):
    """
    Convert pandas and NumPy values into values supported by pyodbc.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, Decimal):
        return value

    return value


def get_sql_driver():
    """
    Select the best available Microsoft SQL Server ODBC driver.
    """

    available_drivers = pyodbc.drivers()

    preferred_drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]

    for driver in preferred_drivers:
        if driver in available_drivers:
            return driver

    raise RuntimeError(
        "No Microsoft SQL Server ODBC driver was found. "
        f"Available drivers: {available_drivers}"
    )


def create_connection():
    """
    Create a trusted local SQL Server connection.
    """

    driver = get_sql_driver()

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

    print(f"Using SQL driver: {driver}")
    print(f"Connecting to database: {DATABASE}")

    return pyodbc.connect(
        connection_string,
        autocommit=False,
    )


def build_insert_query():
    """
    Build the parameterised staging-table INSERT statement.
    """

    column_names = ", ".join(
        f"[{column}]" for column in COLUMNS
    )

    placeholders = ", ".join(
        ["?"] * len(COLUMNS)
    )

    return f"""
        INSERT INTO stg.ClaimOperations (
            {column_names}
        )
        VALUES (
            {placeholders}
        );
    """


# ============================================================
# DATA LOADING
# ============================================================

def load_claims(connection, cursor):
    """
    Truncate the SQL staging table and reload all Parquet rows.
    """

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file was not found: {SOURCE_FILE}"
        )

    print("Clearing existing SQL staging data")

    cursor.execute(
        "TRUNCATE TABLE stg.ClaimOperations;"
    )
    connection.commit()

    insert_sql = build_insert_query()

    parquet_file = pq.ParquetFile(SOURCE_FILE)

    loaded_rows = 0
    batch_number = 0

    cursor.fast_executemany = True

    for record_batch in parquet_file.iter_batches(
        batch_size=BATCH_SIZE,
        columns=COLUMNS,
    ):
        batch_number += 1

        batch_df = record_batch.to_pandas()

        rows = [
            tuple(
                clean_value(value)
                for value in row
            )
            for row in batch_df.itertuples(
                index=False,
                name=None,
            )
        ]

        try:
            cursor.executemany(
                insert_sql,
                rows,
            )
            connection.commit()

        except pyodbc.Error as error:
            connection.rollback()

            print(
                f"Fast insertion failed for batch {batch_number}. "
                "Retrying with standard insertion."
            )

            cursor.fast_executemany = False

            try:
                cursor.executemany(
                    insert_sql,
                    rows,
                )
                connection.commit()

            except pyodbc.Error:
                connection.rollback()
                raise

            cursor.fast_executemany = True

        loaded_rows += len(rows)

        print(
            f"Loaded rows: {loaded_rows:,}"
        )

    print(
        f"\nParquet loading completed: {loaded_rows:,} rows"
    )


# ============================================================
# SQL VALIDATION
# ============================================================

def validate_sql_data(cursor):
    """
    Validate SQL row counts, unique claim keys and financial totals.
    """

    validation_sql = """
        SELECT
            COUNT(*) AS LoadedRows,
            COUNT(DISTINCT CLAIM_KEY) AS UniqueClaimKeys,
            SUM(BILLED_AMOUNT) AS TotalBilledAmount,
            SUM(APPROVED_AMOUNT) AS TotalApprovedAmount,
            SUM(PAID_AMOUNT) AS TotalPaidAmount
        FROM stg.ClaimOperations;
    """

    result = cursor.execute(
        validation_sql
    ).fetchone()

    if result is None:
        raise RuntimeError(
            "SQL validation query returned no result."
        )

    sql_loaded_rows = int(result[0])
    unique_claim_keys = int(result[1])
    total_billed = result[2]
    total_approved = result[3]
    total_paid = result[4]

    print("\nSQL staging validation")
    print("-" * 45)
    print(f"Rows: {sql_loaded_rows:,}")
    print(f"Unique claim keys: {unique_claim_keys:,}")
    print(f"Total billed amount: {total_billed}")
    print(f"Total approved amount: {total_approved}")
    print(f"Total paid amount: {total_paid}")

    if sql_loaded_rows != EXPECTED_ROWS:
        raise ValueError(
            f"SQL contains {sql_loaded_rows:,} rows, "
            f"but {EXPECTED_ROWS:,} were expected."
        )

    if unique_claim_keys != sql_loaded_rows:
        duplicate_count = (
            sql_loaded_rows - unique_claim_keys
        )

        raise ValueError(
            f"{duplicate_count:,} duplicate claim keys "
            "were found in SQL."
        )

    print("-" * 45)
    print("SQL staging validation: PASS")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():
    connection = None
    cursor = None

    try:
        connection = create_connection()
        cursor = connection.cursor()

        if LOAD_DATA:
            print("\nFull reload mode is enabled")
            load_claims(
                connection,
                cursor,
            )
        else:
            print(
                "\nValidation-only mode is enabled. "
                "Existing SQL data will not be reloaded."
            )

        validate_sql_data(cursor)

        print(
            "\nSQL staging process completed successfully."
        )

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print(
            f"\nSQL staging process failed: {error}"
        )

        raise

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()

        print("SQL connection closed.")


if __name__ == "__main__":
    main()