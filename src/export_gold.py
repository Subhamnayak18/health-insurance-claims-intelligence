import argparse
from pathlib import Path

from src.utils.spark import ROOT, create_spark


TABLES = ("dim_date", "dim_provider", "fact_claim", "monthly_claims", "provider_claims")


def export_gold(spark, data_dir, output_dir):
    if not (data_dir / "state/claims.json").exists() or (data_dir / "state/incomplete").exists():
        raise ValueError("Run the pipeline successfully before exporting Gold")
    for name in TABLES:
        table = spark.read.format("delta").load(str(data_dir / "gold" / name))
        table.write.mode("overwrite").parquet(str(output_dir / name))


def main():
    parser = argparse.ArgumentParser(description="Export current Delta snapshots for SQL and Power BI")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/lakehouse")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/exports/gold")
    args = parser.parse_args()
    spark = create_spark()
    try:
        export_gold(spark, args.data_dir, args.output_dir)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
