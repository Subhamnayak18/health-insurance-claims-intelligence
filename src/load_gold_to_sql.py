import argparse
from pathlib import Path

import pyarrow.dataset as ds

from src.utils.sql import create_connection


ROOT = Path(__file__).resolve().parents[1]
TABLES = ("dim_date", "dim_provider", "fact_claim", "monthly_claims", "provider_claims")


def load_gold(connection, export_dir):
    datasets = {name: ds.dataset(export_dir / name, format="parquet") for name in TABLES}
    counts = {name: table.count_rows() for name, table in datasets.items()}
    if any(count == 0 for count in counts.values()):
        raise ValueError("Gold exports must be nonempty")
    cursor = connection.cursor()
    try:
        cursor.execute("SET XACT_ABORT ON;")
        for name in ("fact_claim", "dim_date", "dim_provider", "monthly_claims", "provider_claims"):
            cursor.execute(f"DELETE FROM lake.[{name}]")
        cursor.fast_executemany = True
        for name, table in datasets.items():
            columns = table.schema.names
            if any(not column.replace("_", "").isalnum() for column in columns):
                raise ValueError("Unexpected export column name")
            query = f"INSERT INTO lake.[{name}] ({', '.join('[' + column + ']' for column in columns)}) VALUES ({', '.join('?' for _ in columns)})"
            for batch in table.to_batches(batch_size=5000):
                records = [tuple(row[column] for column in columns) for row in batch.to_pylist()]
                cursor.executemany(query, records)
            loaded = cursor.execute(f"SELECT COUNT_BIG(*) FROM lake.[{name}]").fetchone()[0]
            if loaded != counts[name]:
                raise ValueError(f"Row reconciliation failed: {name}")
        cursor.execute("""
            IF (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.fact_claim) <>
               (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.monthly_claims)
                THROW 51000, 'Gold payment reconciliation failed', 1;
        """)
        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Transactionally replace lake schema tables from Gold exports")
    parser.add_argument("--export-dir", type=Path, default=ROOT / "data/exports/gold")
    args = parser.parse_args()
    connection = create_connection()
    try:
        print(load_gold(connection, args.export_dir))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
