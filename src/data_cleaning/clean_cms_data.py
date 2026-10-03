from pathlib import Path
import logging
import shutil

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "cms_synthetic_claims" / "extracted"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "clean"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
DOCS_DIR = PROJECT_ROOT / "docs" / "02_data_understanding"

CHUNK_SIZE = 50_000

DATASETS = {
    "beneficiary_2023": "beneficiary_2023.csv",
    "carrier": "carrier.csv",
    "inpatient": "inpatient.csv",
    "outpatient": "outpatient.csv",
}

NA_VALUES = [
    "",
    "NULL",
    "null",
    "NA",
    "N/A",
    "None",
    "NONE",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def standardise_chunk(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe.columns = [
        str(column).strip().upper()
        for column in dataframe.columns
    ]

    for column in dataframe.columns:
        values = dataframe[column].astype("string").str.strip()
        dataframe[column] = values.mask(values.eq(""))

    return dataframe


def remove_exact_duplicates(
    dataframe: pd.DataFrame,
    seen_hashes: set[int],
) -> tuple[pd.DataFrame, int]:
    comparison_data = dataframe.fillna("<NA>")

    row_hashes = pd.util.hash_pandas_object(
        comparison_data,
        index=False,
    ).astype("uint64")

    duplicate_mask = (
        row_hashes.duplicated(keep="first")
        | row_hashes.isin(seen_hashes)
    )

    unique_hashes = row_hashes.loc[~duplicate_mask]
    seen_hashes.update(int(value) for value in unique_hashes)

    cleaned = dataframe.loc[~duplicate_mask].copy()

    return cleaned, int(duplicate_mask.sum())


def process_dataset(
    dataset_name: str,
    file_name: str,
) -> dict[str, object]:
    source_path = RAW_DIR / file_name
    dataset_output_dir = OUTPUT_DIR / dataset_name

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_path}"
        )

    if dataset_output_dir.exists():
        shutil.rmtree(dataset_output_dir)

    dataset_output_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes: set[int] = set()

    raw_rows = 0
    cleaned_rows = 0
    duplicates_removed = 0
    missing_cells = 0
    source_column_count = 0
    output_parts = 0
    source_row_start = 2

    bene_id_missing = 0
    clm_id_missing = 0
    clm_id_available = False

    logger.info("Cleaning %s", file_name)

    reader = pd.read_csv(
        source_path,
        sep="|",
        dtype="string",
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        keep_default_na=True,
        na_values=NA_VALUES,
        on_bad_lines="error",
    )

    for chunk_number, chunk in enumerate(reader, start=1):
        input_rows = len(chunk)
        raw_rows += input_rows

        source_row_numbers = pd.Series(
            range(
                source_row_start,
                source_row_start + input_rows,
            ),
            index=chunk.index,
        )

        source_row_start += input_rows

        chunk = standardise_chunk(chunk)

        if source_column_count == 0:
            source_column_count = chunk.shape[1]

        missing_cells += int(
            chunk.isna().sum().sum()
        )

        cleaned_chunk, duplicate_count = remove_exact_duplicates(
            dataframe=chunk,
            seen_hashes=seen_hashes,
        )

        duplicates_removed += duplicate_count
        cleaned_rows += len(cleaned_chunk)

        if "BENE_ID" in cleaned_chunk.columns:
            bene_id_missing += int(
                cleaned_chunk["BENE_ID"].isna().sum()
            )

        if "CLM_ID" in cleaned_chunk.columns:
            clm_id_available = True
            clm_id_missing += int(
                cleaned_chunk["CLM_ID"].isna().sum()
            )

        cleaned_chunk.insert(
            0,
            "SOURCE_ROW_NUMBER",
            source_row_numbers.loc[cleaned_chunk.index].to_numpy(),
        )

        cleaned_chunk.insert(
            0,
            "SOURCE_FILE",
            file_name,
        )

        cleaned_chunk.insert(
            0,
            "SOURCE_DATASET",
            dataset_name,
        )

        cleaned_chunk.insert(
            0,
            "DATA_PROVENANCE",
            "SOURCE_SYNTHETIC_CMS",
        )

        output_parts += 1

        output_path = (
            dataset_output_dir
            / f"part-{chunk_number:05d}.parquet"
        )

        cleaned_chunk.to_parquet(
            output_path,
            index=False,
            compression="snappy",
        )

    output_size_bytes = sum(
        path.stat().st_size
        for path in dataset_output_dir.glob("*.parquet")
    )

    missing_percentage = round(
        missing_cells
        / max(raw_rows * source_column_count, 1)
        * 100,
        2,
    )

    logger.info(
        "%s: %s rows written, %s duplicates removed",
        dataset_name,
        f"{cleaned_rows:,}",
        f"{duplicates_removed:,}",
    )

    return {
        "dataset_name": dataset_name,
        "source_file": file_name,
        "raw_rows": raw_rows,
        "cleaned_rows": cleaned_rows,
        "duplicates_removed": duplicates_removed,
        "source_column_count": source_column_count,
        "output_column_count": source_column_count + 4,
        "missing_cells_after_standardisation": missing_cells,
        "missing_cell_percentage": missing_percentage,
        "bene_id_missing": bene_id_missing,
        "clm_id_available": clm_id_available,
        "clm_id_missing": (
            clm_id_missing if clm_id_available else None
        ),
        "output_parts": output_parts,
        "output_size_mb": round(
            output_size_bytes / (1024**2),
            2,
        ),
    }


def write_report(audit: pd.DataFrame) -> None:
    lines = [
        "# Cleaning Execution Summary",
        "",
        "## Cleaning Actions",
        "",
        "- Standardised column names.",
        "- Trimmed leading and trailing spaces.",
        "- Standardised blank and null values.",
        "- Removed exact duplicate rows using row hashes.",
        "- Added data-lineage columns.",
        "- Saved cleaned data as compressed Parquet files.",
        "",
        "No sparse or constant columns were removed.",
        "",
        "## Dataset Results",
        "",
    ]

    for row in audit.itertuples(index=False):
        lines.extend(
            [
                f"### {row.dataset_name}",
                "",
                f"- Raw rows: {row.raw_rows:,}",
                f"- Cleaned rows: {row.cleaned_rows:,}",
                f"- Exact duplicates removed: {row.duplicates_removed:,}",
                f"- Source columns: {row.source_column_count}",
                f"- Output Parquet parts: {row.output_parts}",
                f"- Missing-cell percentage: {row.missing_cell_percentage}%",
                f"- Missing `BENE_ID`: {row.bene_id_missing:,}",
                "",
            ]
        )

    lines.extend(
        [
            "## Data Lineage Fields",
            "",
            "- `DATA_PROVENANCE`",
            "- `SOURCE_DATASET`",
            "- `SOURCE_FILE`",
            "- `SOURCE_ROW_NUMBER`",
            "",
            "## Governance",
            "",
            "The original CMS files remain unchanged. All cleaned outputs are "
            "stored separately under `data/processed/clean`.",
        ]
    )

    report_path = DOCS_DIR / "04_cleaning_execution_summary.md"

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    audit_records = [
        process_dataset(dataset_name, file_name)
        for dataset_name, file_name in DATASETS.items()
    ]

    audit = pd.DataFrame(audit_records)

    audit_path = (
        METADATA_DIR
        / "cleaning_audit_summary.csv"
    )

    audit.to_csv(
        audit_path,
        index=False,
    )

    write_report(audit)

    logger.info("Cleaning audit saved to %s", audit_path)
    logger.info("CMS cleaning completed successfully")


if __name__ == "__main__":
    main()