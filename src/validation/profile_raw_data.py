from pathlib import Path
import logging

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "cms_synthetic_claims" / "extracted"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
DOCS_DIR = PROJECT_ROOT / "docs" / "02_data_understanding"

SAMPLE_SIZE = 5_000

DATASETS = {
    "beneficiary_2023": "beneficiary_2023.csv",
    "carrier": "carrier.csv",
    "inpatient": "inpatient.csv",
    "outpatient": "outpatient.csv",
}

NA_VALUES = ["", "NULL", "null", "NA", "N/A"]

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def count_rows(file_path: Path) -> int:
    """Return the number of data rows, excluding the header."""

    with file_path.open(
        mode="r",
        encoding="utf-8-sig",
        errors="replace",
    ) as file:
        return max(sum(1 for _ in file) - 1, 0)


def load_sample(file_path: Path) -> pd.DataFrame:
    """Load a sample while preserving identifiers and coded fields."""

    dataframe = pd.read_csv(
        file_path,
        sep="|",
        nrows=SAMPLE_SIZE,
        dtype="string",
        encoding="utf-8-sig",
        keep_default_na=True,
        na_values=NA_VALUES,
        on_bad_lines="warn",
    )

    dataframe.columns = dataframe.columns.str.strip()

    return dataframe


def profile_columns(
    dataframe: pd.DataFrame,
    dataset_name: str,
) -> list[dict[str, object]]:
    """Create column-level quality statistics."""

    records: list[dict[str, object]] = []

    for column_name in dataframe.columns:
        column = dataframe[column_name]

        examples = (
            column.dropna()
            .drop_duplicates()
            .astype(str)
            .head(3)
            .tolist()
        )

        records.append(
            {
                "dataset_name": dataset_name,
                "column_name": column_name,
                "sample_dtype": str(column.dtype),
                "sample_row_count": len(dataframe),
                "missing_count": int(column.isna().sum()),
                "missing_percentage": round(
                    column.isna().mean() * 100,
                    2,
                ),
                "unique_count": int(
                    column.nunique(dropna=True)
                ),
                "example_values": " | ".join(examples),
            }
        )

    return records


def profile_dataset(
    dataset_name: str,
    file_path: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Create dataset-level and column-level profiles."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required source file was not found: {file_path}"
        )

    logger.info("Profiling %s", file_path.name)

    dataframe = load_sample(file_path)
    total_rows = count_rows(file_path)

    duplicate_count = int(dataframe.duplicated().sum())

    summary = {
        "dataset_name": dataset_name,
        "file_name": file_path.name,
        "file_size_mb": round(
            file_path.stat().st_size / (1024**2),
            2,
        ),
        "total_rows": total_rows,
        "column_count": dataframe.shape[1],
        "sample_rows_profiled": dataframe.shape[0],
        "duplicate_rows_in_sample": duplicate_count,
        "duplicate_percentage_in_sample": round(
            duplicate_count / max(len(dataframe), 1) * 100,
            2,
        ),
        "bene_id_present": "BENE_ID" in dataframe.columns,
        "clm_id_present": "CLM_ID" in dataframe.columns,
    }

    logger.info(
        "%s: %s rows, %s columns, %s sample duplicates",
        file_path.name,
        f"{total_rows:,}",
        dataframe.shape[1],
        duplicate_count,
    )

    return summary, profile_columns(
        dataframe=dataframe,
        dataset_name=dataset_name,
    )


def write_markdown_report(
    summary: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a concise profiling report for project documentation."""

    lines = [
        "# Raw Data Profile Summary",
        "",
        "## Purpose",
        "",
        "This report documents the initial structure and quality of the selected "
        "CMS synthetic claims files. No raw source files were modified.",
        "",
        "## Dataset Results",
        "",
    ]

    for row in summary.itertuples(index=False):
        lines.extend(
            [
                f"### {row.dataset_name}",
                "",
                f"- Source file: `{row.file_name}`",
                f"- Total rows: {row.total_rows:,}",
                f"- Number of columns: {row.column_count}",
                f"- Sample rows profiled: {row.sample_rows_profiled:,}",
                f"- Exact duplicate rows in sample: {row.duplicate_rows_in_sample:,}",
                f"- `BENE_ID` available: {row.bene_id_present}",
                f"- `CLM_ID` available: {row.clm_id_present}",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
            "- Repeated claim IDs may represent valid claim lines.",
            "- Exact duplicate rows require separate investigation.",
            "- Claim-header amounts may repeat across claim-line records.",
            "- Missing values are not automatically data-quality errors because "
            "some fields apply only to specific claim types.",
            "",
            "## Status",
            "",
            "This profiling stage is descriptive only. No records or columns "
            "have been removed.",
        ]
    )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    dataset_summaries: list[dict[str, object]] = []
    column_profiles: list[dict[str, object]] = []

    for dataset_name, file_name in DATASETS.items():
        summary, columns = profile_dataset(
            dataset_name=dataset_name,
            file_path=RAW_DATA_DIR / file_name,
        )

        dataset_summaries.append(summary)
        column_profiles.extend(columns)

    summary_dataframe = pd.DataFrame(dataset_summaries)
    column_profile_dataframe = pd.DataFrame(column_profiles)

    summary_path = METADATA_DIR / "raw_data_profile_summary.csv"
    column_profile_path = METADATA_DIR / "raw_column_profile.csv"
    report_path = DOCS_DIR / "02_raw_profile_summary.md"

    summary_dataframe.to_csv(
        summary_path,
        index=False,
    )

    column_profile_dataframe.to_csv(
        column_profile_path,
        index=False,
    )

    write_markdown_report(
        summary=summary_dataframe,
        output_path=report_path,
    )

    logger.info("Dataset summary saved to %s", summary_path)
    logger.info("Column profile saved to %s", column_profile_path)
    logger.info("Documentation saved to %s", report_path)
    logger.info("Raw-data profiling completed successfully")


if __name__ == "__main__":
    main()