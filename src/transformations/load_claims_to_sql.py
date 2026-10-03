import argparse
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.utils.sql import create_connection


ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = ROOT / "data/processed/synthetic/claim_operations.parquet"
BATCH_SIZE = 5_000

COLUMNS = [
    'CLAIM_KEY',
    'CLAIM_ID',
    'CLAIM_TYPE',
    'BENE_ID',
    'POLICY_ID',
    'PLAN_ID',
    'PRIMARY_PROVIDER_ID',
    'CLAIM_FROM_DATE',
    'CLAIM_THRU_DATE',
    'SUBMISSION_DATE',
    'DECISION_DATE',
    'PAYMENT_DATE',
    'CLAIM_STATUS',
    'DENIAL_REASON',
    'PAYMENT_STATUS',
    'DOCUMENTS_COMPLETE_FLAG',
    'POLICY_ACTIVE_FLAG',
    'TREATMENT_COVERED_FLAG',
    'WAITING_PERIOD_FLAG',
    'PREAUTH_REQUIRED_FLAG',
    'PREAUTH_STATUS',
    'BILLED_AMOUNT',
    'ELIGIBLE_AMOUNT',
    'DEDUCTIBLE_AMOUNT',
    'COPAY_AMOUNT',
    'NON_PAYABLE_AMOUNT',
    'ADJUSTMENT_AMOUNT',
    'APPROVED_AMOUNT',
    'PAID_AMOUNT',
    'SOURCE_CMS_PAYMENT_AMOUNT',
    'TURNAROUND_DAYS',
    'SLA_TARGET_DAYS',
    'SLA_BREACH_FLAG',
    'MANUAL_REVIEW_FLAG',
    'DUPLICATE_INDICATOR',
    'HIGH_COST_FLAG',
    'PROVIDER_RISK_SCORE',
    'FRAUD_ALERT_FLAG',
    'ESTIMATED_LEAKAGE_AMOUNT',
    'REVIEW_PRIORITY',
    'QUEUE_NAME',
    'ADJUSTER_ID',
    'ANALYSIS_DATE',
    'DATA_PROVENANCE',
]


def clean_value(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.generic):
        return value.item()
    return value


def build_insert_query():
    columns = ", ".join(f"[{name}]" for name in COLUMNS)
    parameters = ", ".join("?" for _ in COLUMNS)
    return f"INSERT INTO stg.ClaimOperations ({columns}) VALUES ({parameters})"


def validate_sql_data(cursor, source_file=SOURCE_FILE):
    source = pd.read_parquet(source_file, columns=["CLAIM_KEY", "BILLED_AMOUNT", "APPROVED_AMOUNT", "PAID_AMOUNT"])
    if source.empty or source.CLAIM_KEY.isna().any() or source.CLAIM_KEY.duplicated().any():
        raise ValueError("Source must contain nonempty, unique claim keys")
    result = cursor.execute("""
        SELECT COUNT_BIG(*), COUNT(DISTINCT CLAIM_KEY),
               SUM(BILLED_AMOUNT), SUM(APPROVED_AMOUNT), SUM(PAID_AMOUNT)
        FROM stg.ClaimOperations
    """).fetchone()
    if result is None or result[0] != len(source) or result[1] != len(source):
        raise ValueError("SQL staging count or unique keys do not match the source")
    for position, column in enumerate(["BILLED_AMOUNT", "APPROVED_AMOUNT", "PAID_AMOUNT"], 2):
        expected = sum((Decimal(str(value)).quantize(Decimal("0.01")) for value in source[column]), Decimal(0))
        if result[position] != expected:
            raise ValueError(f"SQL staging financial reconciliation failed: {column}")
    print(f"SQL staging validation passed: {len(source):,} claims")


def load_claims(connection, cursor, source_file=SOURCE_FILE):
    parquet = pq.ParquetFile(source_file)
    if parquet.metadata.num_rows == 0 or set(COLUMNS) - set(parquet.schema_arrow.names):
        raise ValueError("Source is empty or missing staging columns")
    cursor.execute("SET XACT_ABORT ON;")
    cursor.execute("TRUNCATE TABLE stg.ClaimOperations;")
    cursor.fast_executemany = True
    for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=COLUMNS):
        rows = [tuple(clean_value(value) for value in row)
                for row in batch.to_pandas().itertuples(index=False, name=None)]
        cursor.executemany(build_insert_query(), rows)
    # The caller validates and commits the whole reload, never individual batches.


def main():
    parser = argparse.ArgumentParser(description="Validate or reload the existing operational staging table")
    parser.add_argument("--source", type=Path, default=SOURCE_FILE)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    connection = create_connection()
    try:
        cursor = connection.cursor()
        if args.reload:
            load_claims(connection, cursor, args.source)
        validate_sql_data(cursor, args.source)
        if args.reload:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
