from pathlib import Path
import logging

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "synthetic"
    / "claim_operations.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "excel_exports"
)

METADATA_DIR = PROJECT_ROOT / "data" / "metadata"

DOCS_DIR = (
    PROJECT_ROOT
    / "docs"
    / "02_data_understanding"
)

FULL_EXPORT_PATH = OUTPUT_DIR / "claim_operations_full.csv"
SAMPLE_EXPORT_PATH = OUTPUT_DIR / "claim_operations_sample.csv"
PLAN_LOOKUP_PATH = OUTPUT_DIR / "plan_lookup.csv"
STATUS_LOOKUP_PATH = OUTPUT_DIR / "claim_status_lookup.csv"
DENIAL_LOOKUP_PATH = OUTPUT_DIR / "denial_reason_lookup.csv"

AUDIT_PATH = METADATA_DIR / "excel_export_audit.csv"
DISTRIBUTION_PATH = METADATA_DIR / "excel_sample_distribution.csv"
REPORT_PATH = DOCS_DIR / "08_excel_data_preparation.md"

SAMPLE_SIZE = 50_000
RANDOM_SEED = 42

FINAL_STATUSES = {
    "APPROVED",
    "PARTIALLY_APPROVED",
    "REJECTED",
}

OPEN_STATUSES = {
    "PENDING",
    "MANUAL_REVIEW",
}

EXPORT_COLUMNS = [
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
    "CLAIM_YEAR",
    "CLAIM_MONTH",
    "DECISION_DATE",
    "PAYMENT_DATE",
    "CLAIM_STATUS",
    "CLAIM_STATUS_GROUP",
    "FINAL_DECISION_FLAG",
    "DENIAL_REASON",
    "PAYMENT_STATUS",
    "DOCUMENTS_COMPLETE_FLAG",
    "DOCUMENT_STATUS",
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
    "CLAIMED_TO_APPROVED_VARIANCE",
    "APPROVED_TO_PAID_VARIANCE",
    "SOURCE_CMS_PAYMENT_AMOUNT",
    "TURNAROUND_DAYS",
    "OPEN_CLAIM_AGE_DAYS",
    "CLAIM_AGE_BUCKET",
    "SLA_TARGET_DAYS",
    "SLA_BREACH_FLAG",
    "SLA_STATUS",
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

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def validate_input(dataframe: pd.DataFrame) -> None:
    required_columns = {
        "CLAIM_KEY",
        "CLAIM_TYPE",
        "CLAIM_STATUS",
        "SUBMISSION_DATE",
        "ANALYSIS_DATE",
        "BILLED_AMOUNT",
        "APPROVED_AMOUNT",
        "PAID_AMOUNT",
    }

    missing_columns = sorted(
        required_columns.difference(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Required columns are missing: {missing_columns}"
        )

    duplicate_keys = int(
        dataframe["CLAIM_KEY"].duplicated().sum()
    )

    if duplicate_keys:
        raise ValueError(
            f"{duplicate_keys} duplicate claim keys were found."
        )


def add_excel_fields(dataframe: pd.DataFrame) -> pd.DataFrame:
    data = dataframe.copy()

    date_columns = [
        "CLAIM_FROM_DATE",
        "CLAIM_THRU_DATE",
        "SUBMISSION_DATE",
        "DECISION_DATE",
        "PAYMENT_DATE",
        "ANALYSIS_DATE",
    ]

    for column in date_columns:
        data[column] = pd.to_datetime(
            data[column],
            errors="coerce",
        )

    open_mask = data["CLAIM_STATUS"].isin(OPEN_STATUSES)

    data["CLAIM_YEAR"] = (
        data["SUBMISSION_DATE"]
        .dt.year
        .astype("Int64")
    )

    data["CLAIM_MONTH"] = (
        data["SUBMISSION_DATE"]
        .dt.to_period("M")
        .astype("string")
    )

    data["CLAIM_STATUS_GROUP"] = np.where(
        open_mask,
        "OPEN",
        "FINAL",
    )

    data["FINAL_DECISION_FLAG"] = (
        data["CLAIM_STATUS"].isin(FINAL_STATUSES)
    )

    data["DOCUMENT_STATUS"] = np.where(
        data["DOCUMENTS_COMPLETE_FLAG"],
        "COMPLETE",
        "INCOMPLETE",
    )

    data["SLA_STATUS"] = np.where(
        data["SLA_BREACH_FLAG"],
        "BREACHED",
        "WITHIN_SLA",
    )

    open_age_days = (
        data["ANALYSIS_DATE"]
        - data["SUBMISSION_DATE"]
    ).dt.days

    open_age_days = (
        open_age_days
        .clip(lower=0)
        .fillna(0)
        .astype("Int64")
    )

    data["OPEN_CLAIM_AGE_DAYS"] = (
        open_age_days.where(open_mask, 0)
    )

    age_bucket = pd.cut(
        open_age_days.astype("float64"),
        bins=[-1, 7, 15, 30, 60, np.inf],
        labels=[
            "0-7 Days",
            "8-15 Days",
            "16-30 Days",
            "31-60 Days",
            "61+ Days",
        ],
    ).astype("string")

    data["CLAIM_AGE_BUCKET"] = age_bucket.where(
        open_mask,
        "CLOSED",
    )

    data["CLAIMED_TO_APPROVED_VARIANCE"] = (
        data["BILLED_AMOUNT"]
        - data["APPROVED_AMOUNT"]
    ).round(2)

    data["APPROVED_TO_PAID_VARIANCE"] = (
        data["APPROVED_AMOUNT"]
        - data["PAID_AMOUNT"]
    ).round(2)

    return data


def create_stratified_sample(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    if len(dataframe) <= SAMPLE_SIZE:
        return dataframe.copy()

    fraction = SAMPLE_SIZE / len(dataframe)

    sample = (
        dataframe.groupby(
            ["CLAIM_TYPE", "CLAIM_STATUS"],
            group_keys=False,
            observed=True,
        )
        .sample(
            frac=fraction,
            random_state=RANDOM_SEED,
        )
    )

    if len(sample) < SAMPLE_SIZE:
        remaining = dataframe.drop(
            index=sample.index
        )

        extra_rows = remaining.sample(
            n=SAMPLE_SIZE - len(sample),
            random_state=RANDOM_SEED,
        )

        sample = pd.concat(
            [sample, extra_rows],
            ignore_index=False,
        )

    if len(sample) > SAMPLE_SIZE:
        sample = sample.sample(
            n=SAMPLE_SIZE,
            random_state=RANDOM_SEED,
        )

    return (
        sample.sample(
            frac=1,
            random_state=RANDOM_SEED,
        )
        .reset_index(drop=True)
    )


def write_lookup_tables() -> None:
    plan_lookup = pd.DataFrame(
        [
            {
                "PLAN_ID": "PLAN_BASIC",
                "PLAN_NAME": "Basic Plan",
                "DEDUCTIBLE_RATE": 0.08,
                "COPAY_RATE": 0.15,
                "COVERAGE_TIER": "Entry",
            },
            {
                "PLAN_ID": "PLAN_STANDARD",
                "PLAN_NAME": "Standard Plan",
                "DEDUCTIBLE_RATE": 0.04,
                "COPAY_RATE": 0.10,
                "COVERAGE_TIER": "Mid",
            },
            {
                "PLAN_ID": "PLAN_PREMIUM",
                "PLAN_NAME": "Premium Plan",
                "DEDUCTIBLE_RATE": 0.01,
                "COPAY_RATE": 0.05,
                "COVERAGE_TIER": "High",
            },
        ]
    )

    status_lookup = pd.DataFrame(
        [
            {
                "CLAIM_STATUS": "APPROVED",
                "STATUS_GROUP": "FINAL",
                "STATUS_SORT_ORDER": 1,
                "IS_OPEN": False,
            },
            {
                "CLAIM_STATUS": "PARTIALLY_APPROVED",
                "STATUS_GROUP": "FINAL",
                "STATUS_SORT_ORDER": 2,
                "IS_OPEN": False,
            },
            {
                "CLAIM_STATUS": "REJECTED",
                "STATUS_GROUP": "FINAL",
                "STATUS_SORT_ORDER": 3,
                "IS_OPEN": False,
            },
            {
                "CLAIM_STATUS": "PENDING",
                "STATUS_GROUP": "OPEN",
                "STATUS_SORT_ORDER": 4,
                "IS_OPEN": True,
            },
            {
                "CLAIM_STATUS": "MANUAL_REVIEW",
                "STATUS_GROUP": "OPEN",
                "STATUS_SORT_ORDER": 5,
                "IS_OPEN": True,
            },
        ]
    )

    denial_lookup = pd.DataFrame(
        [
            {
                "DENIAL_REASON": "POLICY_INACTIVE",
                "DENIAL_DESCRIPTION": "Policy was inactive on the service date.",
                "BUSINESS_OWNER": "Policy Operations",
            },
            {
                "DENIAL_REASON": "TREATMENT_NOT_COVERED",
                "DENIAL_DESCRIPTION": "Treatment was outside plan coverage.",
                "BUSINESS_OWNER": "Product and Benefits",
            },
            {
                "DENIAL_REASON": "WAITING_PERIOD",
                "DENIAL_DESCRIPTION": "Required waiting period was incomplete.",
                "BUSINESS_OWNER": "Policy Operations",
            },
            {
                "DENIAL_REASON": "PREAUTH_DENIED",
                "DENIAL_DESCRIPTION": "Required pre-authorisation was denied.",
                "BUSINESS_OWNER": "Medical Review",
            },
            {
                "DENIAL_REASON": "OTHER",
                "DENIAL_DESCRIPTION": "Other documented adjudication reason.",
                "BUSINESS_OWNER": "Claims Operations",
            },
        ]
    )

    plan_lookup.to_csv(
        PLAN_LOOKUP_PATH,
        index=False,
    )

    status_lookup.to_csv(
        STATUS_LOOKUP_PATH,
        index=False,
    )

    denial_lookup.to_csv(
        DENIAL_LOOKUP_PATH,
        index=False,
    )


def build_distribution_audit(
    full_data: pd.DataFrame,
    sample_data: pd.DataFrame,
) -> pd.DataFrame:
    full_distribution = (
        full_data.groupby(
            ["CLAIM_TYPE", "CLAIM_STATUS"],
            observed=True,
        )
        .size()
        .rename("FULL_ROWS")
    )

    sample_distribution = (
        sample_data.groupby(
            ["CLAIM_TYPE", "CLAIM_STATUS"],
            observed=True,
        )
        .size()
        .rename("SAMPLE_ROWS")
    )

    distribution = pd.concat(
        [full_distribution, sample_distribution],
        axis=1,
    ).fillna(0).reset_index()

    distribution["FULL_PERCENTAGE"] = (
        distribution["FULL_ROWS"]
        / len(full_data)
        * 100
    ).round(2)

    distribution["SAMPLE_PERCENTAGE"] = (
        distribution["SAMPLE_ROWS"]
        / len(sample_data)
        * 100
    ).round(2)

    return distribution


def write_report(
    full_data: pd.DataFrame,
    sample_data: pd.DataFrame,
) -> None:
    lines = [
        "# Excel Data Preparation",
        "",
        "## Purpose",
        "",
        "This step prepares business-friendly source files for Excel.",
        "",
        "## Files",
        "",
        f"- Full Power Query source: `{FULL_EXPORT_PATH.name}`",
        f"- Worksheet sample: `{SAMPLE_EXPORT_PATH.name}`",
        f"- Full rows: {len(full_data):,}",
        f"- Sample rows: {len(sample_data):,}",
        "",
        "## Excel Loading Strategy",
        "",
        "- Load the full claim file through Power Query.",
        "- Load the full file to the Data Model rather than directly to a worksheet.",
        "- Use the 50,000-row sample for formulas, manual checks and demonstrations.",
        "- Use the lookup tables for XLOOKUP and business descriptions.",
        "",
        "## Important Control",
        "",
        "The sample is proportionally selected across claim type and claim status.",
        "",
        "## Data Provenance",
        "",
        "The exported workflow fields remain classified as `PROJECT_SYNTHETIC`.",
    ]

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file was not found: {INPUT_PATH}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading claim operations")

    claim_operations = pd.read_parquet(INPUT_PATH)

    validate_input(claim_operations)

    excel_data = add_excel_fields(
        claim_operations
    )

    missing_export_columns = [
        column
        for column in EXPORT_COLUMNS
        if column not in excel_data.columns
    ]

    if missing_export_columns:
        raise ValueError(
            f"Excel export columns are missing: "
            f"{missing_export_columns}"
        )

    excel_data = excel_data[EXPORT_COLUMNS]

    sample_data = create_stratified_sample(
        excel_data
    )

    logger.info("Writing full Excel source")

    excel_data.to_csv(
        FULL_EXPORT_PATH,
        index=False,
        date_format="%Y-%m-%d",
    )

    logger.info("Writing worksheet sample")

    sample_data.to_csv(
        SAMPLE_EXPORT_PATH,
        index=False,
        date_format="%Y-%m-%d",
    )

    write_lookup_tables()

    distribution = build_distribution_audit(
        full_data=excel_data,
        sample_data=sample_data,
    )

    distribution.to_csv(
        DISTRIBUTION_PATH,
        index=False,
    )

    audit = pd.DataFrame(
        [
            {
                "export_name": "claim_operations_full",
                "row_count": len(excel_data),
                "column_count": len(excel_data.columns),
                "duplicate_claim_keys": int(
                    excel_data["CLAIM_KEY"]
                    .duplicated()
                    .sum()
                ),
                "file_size_mb": round(
                    FULL_EXPORT_PATH.stat().st_size
                    / (1024**2),
                    2,
                ),
                "purpose": "Power Query and Data Model",
            },
            {
                "export_name": "claim_operations_sample",
                "row_count": len(sample_data),
                "column_count": len(sample_data.columns),
                "duplicate_claim_keys": int(
                    sample_data["CLAIM_KEY"]
                    .duplicated()
                    .sum()
                ),
                "file_size_mb": round(
                    SAMPLE_EXPORT_PATH.stat().st_size
                    / (1024**2),
                    2,
                ),
                "purpose": "Worksheet formulas and validation",
            },
        ]
    )

    audit.to_csv(
        AUDIT_PATH,
        index=False,
    )

    write_report(
        full_data=excel_data,
        sample_data=sample_data,
    )

    logger.info(
        "Full Excel source created with %s rows",
        f"{len(excel_data):,}",
    )

    logger.info(
        "Excel sample created with %s rows",
        f"{len(sample_data):,}",
    )

    logger.info("Excel export preparation completed")


if __name__ == "__main__":
    main()