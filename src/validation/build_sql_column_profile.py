from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def main():
    data = pd.read_parquet(ROOT / "data/processed/synthetic/claim_operations.parquet")
    records = []
    for name in data.columns:
        values = data[name]
        records.append({
            "column_name": name,
            "pandas_dtype": str(values.dtype),
            "row_count": len(values),
            "non_null_count": int(values.notna().sum()),
            "null_count": int(values.isna().sum()),
            "unique_count": int(values.nunique(dropna=True)),
            "sample_value": str(values.dropna().iloc[0]) if values.notna().any() else None,
        })
    output = ROOT / "data/metadata/sql_source_column_profile.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, index=False)
    print(f"Profiled {len(data):,} rows and {len(data.columns)} columns")


if __name__ == "__main__":
    main()
