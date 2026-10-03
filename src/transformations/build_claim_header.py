from pathlib import Path
import logging

import pandas as pd
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEAN_DIR = PROJECT_ROOT / "data" / "processed" / "clean"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "analytical"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
DOCS_DIR = PROJECT_ROOT / "docs" / "02_data_understanding"

DATASETS = {
    "carrier": CLEAN_DIR / "carrier",
    "inpatient": CLEAN_DIR / "inpatient",
    "outpatient": CLEAN_DIR / "outpatient",
}

FIELD_CANDIDATES = {
    "claim_payment": [
        "CLM_PMT_AMT",
    ],
    "claim_total_charge": [
        "CLM_TOT_CHRG_AMT",
        "CLM_SBMTD_CHRG_AMT",
    ],
    "line_submitted_charge": [
        "LINE_SBMTD_CHRG_AMT",
        "REV_CNTR_TOT_CHRG_AMT",
    ],
    "line_allowed_amount": [
        "LINE_ALOWD_CHRG_AMT",
    ],
    "line_payment": [
        "LINE_NCH_PMT_AMT",
        "REV_CNTR_PMT_AMT",
    ],
    "provider": [
        "PRVDR_NUM",
        "ORG_NPI_NUM",
        "RNDRNG_PHYSN_NPI",
        "AT_PHYSN_NPI",
        "OP_PHYSN_NPI",
    ],
    "procedure": [
        "HCPCS_CD",
        "ICD_PRCDR_CD1",
        "PRCDR_CD",
    ],
    "diagnosis": [
        "PRNCPAL_DGNS_CD",
        "ICD_DGNS_CD1",
        "LINE_ICD_DGNS_CD",
    ],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def get_available_columns(dataset_path: Path) -> list[str]:
    parquet_files = sorted(dataset_path.glob("*.parquet"))

    if not parquet_files:
        raise FileNotFoundError(
            f"No Parquet files found in {dataset_path}"
        )

    return pq.read_schema(parquet_files[0]).names


def coalesce_columns(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> pd.Series:
    available = [
        column
        for column in candidates
        if column in dataframe.columns
    ]

    if not available:
        return pd.Series(
            pd.NA,
            index=dataframe.index,
            dtype="string",
        )

    values = dataframe[available[0]].copy()
    for column in available[1:]:
        values = values.combine_first(dataframe[column])
    return values


def to_numeric(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> pd.Series:
    values = coalesce_columns(
        dataframe=dataframe,
        candidates=candidates,
    )

    return pd.to_numeric(
        values,
        errors="coerce",
    )


def build_dataset_header(
    dataset_name: str,
    dataset_path: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    available_columns = get_available_columns(dataset_path)

    required_columns = [
        "BENE_ID",
        "CLM_ID",
        "CLM_FROM_DT",
        "CLM_THRU_DT",
    ]

    missing_required = [
        column
        for column in required_columns
        if column not in available_columns
    ]

    if missing_required:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{missing_required}"
        )

    optional_columns = {
        column
        for candidates in FIELD_CANDIDATES.values()
        for column in candidates
    }

    selected_columns = required_columns + sorted(
        optional_columns.intersection(available_columns)
    )

    logger.info("Loading %s claim lines", dataset_name)

    source = pd.read_parquet(
        dataset_path,
        columns=selected_columns,
        engine="pyarrow",
    )

    claim_lines = pd.DataFrame(
        {
            "CLAIM_TYPE": dataset_name.upper(),
            "CLAIM_ID": source["CLM_ID"],
            "BENE_ID": source["BENE_ID"],
            "CLAIM_FROM_DATE": pd.to_datetime(
                source["CLM_FROM_DT"],
                errors="coerce",
                format="mixed",
            ),
            "CLAIM_THRU_DATE": pd.to_datetime(
                source["CLM_THRU_DT"],
                errors="coerce",
                format="mixed",
            ),
            "CLAIM_PAYMENT_AMOUNT": to_numeric(
                source,
                FIELD_CANDIDATES["claim_payment"],
            ),
            "CLAIM_TOTAL_CHARGE_AMOUNT": to_numeric(
                source,
                FIELD_CANDIDATES["claim_total_charge"],
            ),
            "LINE_SUBMITTED_CHARGE_AMOUNT": to_numeric(
                source,
                FIELD_CANDIDATES["line_submitted_charge"],
            ),
            "LINE_ALLOWED_AMOUNT": to_numeric(
                source,
                FIELD_CANDIDATES["line_allowed_amount"],
            ),
            "LINE_PAYMENT_AMOUNT": to_numeric(
                source,
                FIELD_CANDIDATES["line_payment"],
            ),
            "PROVIDER_ID": coalesce_columns(
                source,
                FIELD_CANDIDATES["provider"],
            ),
            "PROCEDURE_CODE": coalesce_columns(
                source,
                FIELD_CANDIDATES["procedure"],
            ),
            "DIAGNOSIS_CODE": coalesce_columns(
                source,
                FIELD_CANDIDATES["diagnosis"],
            ),
        }
    )

    grouped = claim_lines.groupby(
        ["CLAIM_TYPE", "CLAIM_ID"],
        sort=False,
        dropna=False,
    )

    header = grouped.agg(
        BENE_ID=("BENE_ID", "first"),
        CLAIM_FROM_DATE=("CLAIM_FROM_DATE", "min"),
        CLAIM_THRU_DATE=("CLAIM_THRU_DATE", "max"),
        CLAIM_PAYMENT_AMOUNT=("CLAIM_PAYMENT_AMOUNT", "first"),
        CLAIM_TOTAL_CHARGE_AMOUNT=(
            "CLAIM_TOTAL_CHARGE_AMOUNT",
            "first",
        ),
        PRIMARY_PROVIDER_ID=("PROVIDER_ID", "first"),
        PRIMARY_PROCEDURE_CODE=("PROCEDURE_CODE", "first"),
        PRIMARY_DIAGNOSIS_CODE=("DIAGNOSIS_CODE", "first"),
        LINE_COUNT=("CLAIM_ID", "size"),
        UNIQUE_PROVIDER_COUNT=("PROVIDER_ID", "nunique"),
        UNIQUE_PROCEDURE_COUNT=("PROCEDURE_CODE", "nunique"),
    ).reset_index()

    line_sums = grouped[
        [
            "LINE_SUBMITTED_CHARGE_AMOUNT",
            "LINE_ALLOWED_AMOUNT",
            "LINE_PAYMENT_AMOUNT",
        ]
    ].sum(min_count=1).reset_index()

    header = header.merge(
        line_sums,
        on=["CLAIM_TYPE", "CLAIM_ID"],
        how="left",
        validate="one_to_one",
    )

    header.insert(
        0,
        "CLAIM_KEY",
        header["CLAIM_TYPE"]
        + "-"
        + header["CLAIM_ID"].astype("string"),
    )

    header["CLAIM_YEAR"] = (
        header["CLAIM_FROM_DATE"]
        .dt.year
        .astype("Int64")
    )

    header["SERVICE_DAYS"] = (
        (
            header["CLAIM_THRU_DATE"]
            - header["CLAIM_FROM_DATE"]
        ).dt.days
        + 1
    ).astype("Int64")

    header["DATA_PROVENANCE"] = "DERIVED"

    audit = {
        "dataset_name": dataset_name,
        "source_line_rows": len(claim_lines),
        "claim_header_rows": len(header),
        "unique_claim_keys": header["CLAIM_KEY"].nunique(),
        "line_count_reconciliation": int(
            header["LINE_COUNT"].sum()
        ),
        "minimum_claim_date": header["CLAIM_FROM_DATE"].min(),
        "maximum_claim_date": header["CLAIM_THRU_DATE"].max(),
        "claim_payment_total": round(
            header["CLAIM_PAYMENT_AMOUNT"].sum(
                min_count=1
            ),
            2,
        ),
    }

    logger.info(
        "%s: %s lines converted into %s claims",
        dataset_name,
        f"{len(claim_lines):,}",
        f"{len(header):,}",
    )

    return header, audit


def write_report(audit: pd.DataFrame) -> None:
    lines = [
        "# Unified Claim Header Build",
        "",
        "## Purpose",
        "",
        "The CMS source files are stored at claim-line grain. "
        "This transformation creates one record per claim.",
        "",
        "## Double-Counting Control",
        "",
        "- `CLM_PMT_AMT` is treated as a claim-level value.",
        "- Claim-level payment is selected once per claim.",
        "- Line-level submitted, allowed and payment amounts are summed.",
        "- `CLAIM_TYPE` and `CLAIM_ID` form the unique claim key.",
        "",
        "## Results",
        "",
    ]

    for row in audit.itertuples(index=False):
        lines.extend(
            [
                f"### {row.dataset_name}",
                "",
                f"- Source claim lines: {row.source_line_rows:,}",
                f"- Claim-header rows: {row.claim_header_rows:,}",
                f"- Unique claim keys: {row.unique_claim_keys:,}",
                (
                    "- Reconciled line count: "
                    f"{row.line_count_reconciliation:,}"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Final Grain",
            "",
            "One row per `CLAIM_TYPE` and `CLAIM_ID`.",
        ]
    )

    report_path = DOCS_DIR / "06_claim_header_build.md"

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    claim_headers = []
    audit_records = []

    for dataset_name, dataset_path in DATASETS.items():
        header, audit = build_dataset_header(
            dataset_name,
            dataset_path,
        )

        claim_headers.append(header)
        audit_records.append(audit)

    unified_header = pd.concat(
        claim_headers,
        ignore_index=True,
    )

    if unified_header["CLAIM_KEY"].duplicated().any():
        raise ValueError(
            "Duplicate CLAIM_KEY values were found."
        )

    output_path = (
        OUTPUT_DIR
        / "claim_header.parquet"
    )

    unified_header.to_parquet(
        output_path,
        index=False,
        compression="snappy",
    )

    audit_dataframe = pd.DataFrame(audit_records)

    audit_path = (
        METADATA_DIR
        / "claim_header_build_audit.csv"
    )

    audit_dataframe.to_csv(
        audit_path,
        index=False,
    )

    write_report(audit_dataframe)

    logger.info(
        "Unified claim header saved with %s claims",
        f"{len(unified_header):,}",
    )


if __name__ == "__main__":
    main()
