import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from src.export_gold import export_gold
from src.ingestion.claims import read_claims
from src.pipeline import run
from src.utils.delta import merge_snapshot


def test_merge_insert_update_delete_and_schema_evolution(spark, tmp_path):
    path = tmp_path / "silver"
    first = spark.createDataFrame([("a", "old", 1), ("b", "removed", 2)], "id string, _row_hash string, amount int")
    merge_snapshot(first, path, ["id"])
    changed = spark.createDataFrame([("a", "new", 3, "added"), ("c", "new", 4, None)],
                                    "id string, _row_hash string, amount int, extra string")
    merge_snapshot(changed, path, ["id"])
    merge_snapshot(changed, path, ["id"])
    rows = spark.read.format("delta").load(str(path)).orderBy("id").collect()
    assert [(row.id, row.amount, row.extra) for row in rows] == [("a", 3, "added"), ("c", 4, None)]
    with pytest.raises(ValueError, match="Breaking Silver schema"):
        merge_snapshot(first, path, ["id"])


@pytest.mark.integration
def test_pipeline_replay_exports_and_quarantine(spark, tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(Path(__file__).parent / "fixtures", raw)
    lake = tmp_path / "lake"
    result = run(spark, raw, lake)
    assert sum(row["claims"] for row in result["summary"]) == 3
    assert sum(row["payment"] for row in result["summary"]) == Decimal("290.00")
    fact = lake / "gold/fact_claim"
    version = DeltaTable.forPath(spark, str(fact)).history(1).first().version
    assert run(spark, raw, lake)["status"] == "unchanged"
    assert DeltaTable.forPath(spark, str(fact)).history(1).first().version == version
    export_gold(spark, lake, tmp_path / "exports")
    assert spark.read.parquet(str(tmp_path / "exports/fact_claim")).count() == 3
    carrier = raw / "carrier.csv"
    original = carrier.read_text()
    carrier.write_text(original.replace("100.00", "120.00"))
    corrected = run(spark, raw, lake)
    assert sum(row["payment"] for row in corrected["summary"]) == Decimal("310.00")
    carrier.write_text(original.replace("100.00", "bad"))
    with pytest.raises(ValueError, match="Quality checks failed"):
        run(spark, raw, lake)
    assert (lake / "state/incomplete").exists()
    with pytest.raises(ValueError):
        export_gold(spark, lake, tmp_path / "exports")
    assert spark.read.format("delta").load(str(lake / "quarantine/carrier/invalid_rows")).count() == 2
    carrier.write_text(original)
    assert sum(row["claims"] for row in run(spark, raw, lake)["summary"]) == 3
    assert not (lake / "state/incomplete").exists()


def test_missing_required_schema_fails(spark, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("BENE_ID|CLM_ID\nb|c\n")
    with pytest.raises(ValueError, match="Missing required"):
        read_claims(spark, path, "carrier", "test")
