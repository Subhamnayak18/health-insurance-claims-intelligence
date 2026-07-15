# Cleaning Execution Summary

## Cleaning Actions

- Standardised column names.
- Trimmed leading and trailing spaces.
- Standardised blank and null values.
- Removed exact duplicate rows using row hashes.
- Added data-lineage columns.
- Saved cleaned data as compressed Parquet files.

No sparse or constant columns were removed.

## Dataset Results

### beneficiary_2023

- Raw rows: 9,179
- Cleaned rows: 9,179
- Exact duplicates removed: 0
- Source columns: 185
- Output Parquet parts: 1
- Missing-cell percentage: 34.16%
- Missing `BENE_ID`: 0

### carrier

- Raw rows: 1,121,004
- Cleaned rows: 1,121,004
- Exact duplicates removed: 0
- Source columns: 96
- Output Parquet parts: 23
- Missing-cell percentage: 19.25%
- Missing `BENE_ID`: 0

### inpatient

- Raw rows: 58,066
- Cleaned rows: 58,066
- Exact duplicates removed: 0
- Source columns: 197
- Output Parquet parts: 2
- Missing-cell percentage: 47.68%
- Missing `BENE_ID`: 0

### outpatient

- Raw rows: 575,092
- Cleaned rows: 575,092
- Exact duplicates removed: 0
- Source columns: 162
- Output Parquet parts: 12
- Missing-cell percentage: 50.26%
- Missing `BENE_ID`: 0

## Data Lineage Fields

- `DATA_PROVENANCE`
- `SOURCE_DATASET`
- `SOURCE_FILE`
- `SOURCE_ROW_NUMBER`

## Governance

The original CMS files remain unchanged. All cleaned outputs are stored separately under `data/processed/clean`.