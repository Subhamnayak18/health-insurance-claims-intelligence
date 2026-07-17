from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    "data/processed/synthetic/claim_operations.parquet"
)

OUTPUT_FILE = Path(
    "data/metadata/sql_source_column_profile.csv"
)

df = pd.read_parquet(INPUT_FILE)

records = []

for column in df.columns:
    series = df[column]

    records.append(
        {
            "column_name": column,
            "pandas_dtype": str(series.dtype),
            "row_count": len(series),
            "non_null_count": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_value": (
                str(series.dropna().iloc[0])
                if series.notna().any()
                else None
            ),
        }
    )

profile = pd.DataFrame(records)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
profile.to_csv(OUTPUT_FILE, index=False)

print("SQL source profiling completed")
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(f"Output: {OUTPUT_FILE}")
print(profile[["column_name", "pandas_dtype"]].to_string(index=False))