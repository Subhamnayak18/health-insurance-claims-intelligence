from pathlib import Path
import logging
import re
import shutil

import pandas as pd
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cms_synthetic_claims"
    / "extracted"
)

CLEAN_DIR = PROJECT_ROOT / "data" / "processed" / "clean"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
DOCS_DIR = PROJECT_ROOT / "docs" / "02_data_understanding"

BENEFICIARY_OUTPUT_DIR = CLEAN_DIR / "beneficiary_history"

CLAIM_DATASETS = {
    "carrier": CLEAN_DIR / "carrier",
    "inpatient": CLEAN_DIR / "inpatient",
    "outpatient": CLEAN_DIR / "outpatient",
}

NA_VALUES = ["", "NULL", "null", "NA", "N/A", "None"]

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def standardise_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe.columns = dataframe.columns.str.strip().str.upper()

    for column in dataframe.columns:
        values = dataframe[column].astype("string").str.strip()
        dataframe[column] = values.mask(values.eq(""))

    return dataframe


def build_beneficiary_history() -> tuple[pd.DataFrame, list[dict]]:
    source_files = sorted(RAW_DIR.glob("beneficiary_*.csv"))

    if not source_files:
        raise FileNotFoundError("No beneficiary files were found.")

    if BENEFICIARY_OUTPUT_DIR.exists():
        shutil.rmtree(BENEFICIARY_OUTPUT_DIR)

    BENEFICIARY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    key_frames = []
    audit_records = []

    for file_path in source_files:
        year_match = re.search(r"(\d{4})", file_path.stem)

        if not year_match:
            raise ValueError(
                f"Could not identify year from {file_path.name}"
            )

        beneficiary_year = int(year_match.group(1))

        logger.info("Processing %s", file_path.name)

        dataframe = pd.read_csv(
            file_path,
            sep="|",
            dtype="string",
            encoding="utf-8-sig",
            keep_default_na=True,
            na_values=NA_VALUES,
        )

        dataframe = standardise_dataframe(dataframe)

        dataframe.insert(0, "BENEFICIARY_YEAR", beneficiary_year)
        dataframe.insert(0, "SOURCE_FILE", file_path.name)
        dataframe.insert(0, "SOURCE_DATASET", "beneficiary_history")
        dataframe.insert(0, "DATA_PROVENANCE", "SOURCE_SYNTHETIC_CMS")

        dataframe.insert(
            4,
            "SOURCE_ROW_NUMBER",
            range(2, len(dataframe) + 2),
        )

        missing_bene_id = int(dataframe["BENE_ID"].isna().sum())

        duplicate_keys = int(
            dataframe.duplicated(
                subset=["BENE_ID", "BENEFICIARY_YEAR"],
                keep=False,
            ).sum()
        )

        output_path = (
            BENEFICIARY_OUTPUT_DIR
            / f"beneficiary_{beneficiary_year}.parquet"
        )

        dataframe.to_parquet(
            output_path,
            index=False,
            compression="snappy",
        )

        key_frames.append(
            dataframe[
                ["BENE_ID", "BENEFICIARY_YEAR"]
            ].copy()
        )

        audit_records.append(
            {
                "beneficiary_year": beneficiary_year,
                "row_count": len(dataframe),
                "missing_bene_id": missing_bene_id,
                "duplicate_beneficiary_year_keys": duplicate_keys,
                "output_file": output_path.name,
            }
        )

    beneficiary_keys = (
        pd.concat(key_frames, ignore_index=True)
        .dropna(subset=["BENE_ID", "BENEFICIARY_YEAR"])
        .drop_duplicates()
    )

    return beneficiary_keys, audit_records


def get_parquet_columns(dataset_path: Path) -> list[str]:
    parquet_files = sorted(dataset_path.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No Parquet files found in {dataset_path}"
        )

    return pq.read_schema(parquet_files[0]).names


def add_result(
    results: list[dict],
    dataset_name: str,
    check_name: str,
    failed_rows: int,
    total_rows: int,
    severity: str,
    description: str,
) -> None:
    if failed_rows == 0:
        status = "PASS"
    elif severity == "Critical":
        status = "FAIL"
    else:
        status = "WARNING"

    results.append(
        {
            "dataset_name": dataset_name,
            "check_name": check_name,
            "status": status,
            "severity": severity,
            "failed_rows": failed_rows,
            "total_rows": total_rows,
            "failure_percentage": round(
                failed_rows / max(total_rows, 1) * 100,
                4,
            ),
            "description": description,
        }
    )


def validate_claim_dataset(
    dataset_name: str,
    dataset_path: Path,
    beneficiary_keys: pd.DataFrame,
) -> list[dict]:
    available_columns = get_parquet_columns(dataset_path)

    required_columns = [
        "BENE_ID",
        "CLM_ID",
        "CLM_FROM_DT",
        "CLM_THRU_DT",
        "CLM_PMT_AMT",
    ]

    line_column = next(
        (
            column
            for column in ["LINE_NUM", "CLM_LINE_NUM"]
            if column in available_columns
        ),
        None,
    )

    selected_columns = [
        column
        for column in required_columns
        if column in available_columns
    ]

    if line_column:
        selected_columns.append(line_column)

    logger.info("Validating %s", dataset_name)

    dataframe = pd.read_parquet(
        dataset_path,
        columns=selected_columns,
        engine="pyarrow",
    )

    total_rows = len(dataframe)
    results: list[dict] = []

    missing_bene_id = int(dataframe["BENE_ID"].isna().sum())
    missing_claim_id = int(dataframe["CLM_ID"].isna().sum())

    add_result(
        results,
        dataset_name,
        "MISSING_BENE_ID",
        missing_bene_id,
        total_rows,
        "Critical",
        "Claim rows must contain a beneficiary identifier.",
    )

    add_result(
        results,
        dataset_name,
        "MISSING_CLM_ID",
        missing_claim_id,
        total_rows,
        "Critical",
        "Claim rows must contain a claim identifier.",
    )

    from_dates = pd.to_datetime(
        dataframe["CLM_FROM_DT"],
        errors="coerce",
        format="mixed",
    )

    through_dates = pd.to_datetime(
        dataframe["CLM_THRU_DT"],
        errors="coerce",
        format="mixed",
    )

    invalid_from_dates = int(
        (
            dataframe["CLM_FROM_DT"].notna()
            & from_dates.isna()
        ).sum()
    )

    invalid_through_dates = int(
        (
            dataframe["CLM_THRU_DT"].notna()
            & through_dates.isna()
        ).sum()
    )

    invalid_date_order = int(
        (
            from_dates.notna()
            & through_dates.notna()
            & (from_dates > through_dates)
        ).sum()
    )

    add_result(
        results,
        dataset_name,
        "INVALID_FROM_DATE",
        invalid_from_dates,
        total_rows,
        "Critical",
        "Claim start dates must be valid dates.",
    )

    add_result(
        results,
        dataset_name,
        "INVALID_THROUGH_DATE",
        invalid_through_dates,
        total_rows,
        "Critical",
        "Claim end dates must be valid dates.",
    )

    add_result(
        results,
        dataset_name,
        "CLAIM_DATE_ORDER",
        invalid_date_order,
        total_rows,
        "Critical",
        "Claim start date must not be after claim end date.",
    )

    payment_amount = pd.to_numeric(
        dataframe["CLM_PMT_AMT"],
        errors="coerce",
    )

    negative_payment_count = int(
        (payment_amount < 0).sum()
    )

    add_result(
        results,
        dataset_name,
        "NEGATIVE_PAYMENT_AMOUNT",
        negative_payment_count,
        total_rows,
        "Warning",
        "Negative values may represent adjustments or reversals and require review.",
    )

    if line_column:
        duplicate_line_keys = int(
            dataframe.duplicated(
                subset=["CLM_ID", line_column],
                keep=False,
            ).sum()
        )

        add_result(
            results,
            dataset_name,
            "DUPLICATE_CLAIM_LINE_KEY",
            duplicate_line_keys,
            total_rows,
            "Critical",
            f"The combination of CLM_ID and {line_column} should identify a claim line.",
        )

    claim_member_year = pd.DataFrame(
        {
            "BENE_ID": dataframe["BENE_ID"],
            "BENEFICIARY_YEAR": from_dates.dt.year.astype("Int64"),
        }
    )

    claim_member_year = claim_member_year.dropna()

    matched = claim_member_year.merge(
        beneficiary_keys.assign(MEMBER_MATCH=1),
        on=["BENE_ID", "BENEFICIARY_YEAR"],
        how="left",
    )

    unmatched_member_year = int(
        matched["MEMBER_MATCH"].isna().sum()
    )

    add_result(
        results,
        dataset_name,
        "UNMATCHED_BENEFICIARY_YEAR",
        unmatched_member_year,
        len(claim_member_year),
        "Warning",
        "Claim beneficiary and claim year should match a beneficiary-year record.",
    )

    return results


def write_report(results: pd.DataFrame) -> None:
    lines = [
        "# Data Quality Validation",
        "",
        "## Purpose",
        "",
        "This report validates beneficiary and claim relationships after cleaning.",
        "",
        "## Validation Results",
        "",
    ]

    for row in results.itertuples(index=False):
        lines.append(
            f"- **{row.dataset_name} — {row.check_name}:** "
            f"{row.status} ({row.failed_rows:,} failed rows)"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `PASS` means no exceptions were found.",
            "- `WARNING` means the records require business review.",
            "- `FAIL` means a critical data-quality rule was violated.",
            "- Negative payments are not automatically deleted because they may "
            "represent legitimate claim reversals or adjustments.",
        ]
    )

    report_path = DOCS_DIR / "05_data_quality_validation.md"

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    beneficiary_keys, beneficiary_audit = build_beneficiary_history()

    beneficiary_audit_dataframe = pd.DataFrame(
        beneficiary_audit
    )

    beneficiary_audit_dataframe.to_csv(
        METADATA_DIR / "beneficiary_history_audit.csv",
        index=False,
    )

    validation_results: list[dict] = []

    duplicate_beneficiary_keys = int(
        beneficiary_keys.duplicated(
            subset=["BENE_ID", "BENEFICIARY_YEAR"],
            keep=False,
        ).sum()
    )

    add_result(
        validation_results,
        "beneficiary_history",
        "DUPLICATE_BENEFICIARY_YEAR_KEY",
        duplicate_beneficiary_keys,
        len(beneficiary_keys),
        "Critical",
        "BENE_ID and BENEFICIARY_YEAR should uniquely identify a beneficiary record.",
    )

    for dataset_name, dataset_path in CLAIM_DATASETS.items():
        validation_results.extend(
            validate_claim_dataset(
                dataset_name,
                dataset_path,
                beneficiary_keys,
            )
        )

    results_dataframe = pd.DataFrame(
        validation_results
    )

    results_path = (
        METADATA_DIR
        / "data_quality_validation_results.csv"
    )

    results_dataframe.to_csv(
        results_path,
        index=False,
    )

    write_report(results_dataframe)

    logger.info("Beneficiary history created successfully")
    logger.info("Validation results saved to %s", results_path)
    logger.info("Clean-data validation completed")


if __name__ == "__main__":
    main()