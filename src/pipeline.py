import argparse
import json
import logging
from functools import reduce
from pathlib import Path

from pyspark.sql import functions as F

from src.ingestion.claims import CLAIM_TYPES, file_digest, read_claims
from src.quality.claims import validate_lines
from src.transformations.spark_claims import build_claim_headers, build_gold, clean_claim_lines
from src.utils.delta import merge_snapshot, write_delta
from src.utils.spark import ROOT, create_spark


def _run(spark, raw_dir, data_dir, force=False):
    raw_dir, data_dir = Path(raw_dir).resolve(), Path(data_dir).resolve()
    if raw_dir == data_dir or data_dir in raw_dir.parents:
        raise ValueError("Output root must not contain the raw source directory")
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "claims.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    sources = {kind: raw_dir / f"{kind}.csv" for kind in CLAIM_TYPES}
    digests = {kind: file_digest(path) for kind, path in sources.items()}
    changed = [kind for kind in CLAIM_TYPES if force or state.get("sources", {}).get(kind) != digests[kind]
               or not (data_dir / "silver" / kind / "_delta_log").exists()]
    if not changed and all((data_dir / "gold" / name / "_delta_log").exists()
                           for name in ("fact_claim", "dim_date", "dim_provider", "monthly_claims", "provider_claims")):
        logging.info("All three source snapshots unchanged; no tables rewritten")
        return {"status": "unchanged", **state}
    audits = state.get("quality", {})
    for kind in changed:
        logging.info("Processing %s", kind)
        bronze = read_claims(spark, sources[kind], kind, digests[kind])
        write_delta(bronze, data_dir / "bronze" / kind)
        bronze = spark.read.format("delta").load(str(data_dir / "bronze" / kind))
        raw_count = bronze.count()
        if raw_count == 0:
            raise ValueError(f"Empty {kind} snapshot; refusing to delete existing claims")
        lines = clean_claim_lines(bronze, kind).persist()
        try:
            clean_count = lines.count()
            quality, rejected = validate_lines(lines)
            audits[kind] = {"raw_lines": raw_count, "clean_lines": clean_count,
                            "exact_duplicates_removed": raw_count - clean_count, **quality}
            for name, df in rejected.items():
                write_delta(df, data_dir / "quarantine" / kind / name)
            if any(quality[name] for name in rejected):
                raise ValueError(f"Quality checks failed for {kind}: {quality}; see quarantine tables")
            merge_snapshot(lines, data_dir / "silver" / kind, ["CLAIM_KEY", "LINE_NUMBER"])
        finally:
            lines.unpersist()
    silver = [spark.read.format("delta").load(str(data_dir / "silver" / kind)) for kind in CLAIM_TYPES]
    lines = reduce(lambda left, right: left.unionByName(right, allowMissingColumns=True), silver)
    headers = build_claim_headers(lines).persist()
    try:
        totals = headers.groupBy("CLAIM_TYPE").agg(
            F.count("*").alias("claims"), F.sum("LINE_COUNT").alias("lines"),
            F.sum("CLAIM_PAYMENT_AMOUNT").alias("payment"),
        ).orderBy("CLAIM_TYPE").collect()
        summary = [row.asDict() for row in totals]
        for row in summary:
            if row["lines"] != audits[row["CLAIM_TYPE"].lower()]["clean_lines"]:
                raise ValueError("Claim-header line reconciliation failed")
        for name, table in build_gold(headers, lines).items():
            write_delta(table, data_dir / "gold" / name)
        result = {"sources": digests, "quality": audits, "summary": summary}
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
        temporary.replace(state_path)
        logging.info("Gold tables published: %s", summary)
        return result
    finally:
        headers.unpersist()


def run(spark, raw_dir, data_dir, force=False):
    state_dir = Path(data_dir) / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "writer.lock"
    dirty = state_dir / "incomplete"
    with lock.open("x"):
        pass
    try:
        recovery = dirty.exists()
        dirty.write_text("Run in progress or incomplete; rerun before exporting.\n")
        result = _run(spark, raw_dir, data_dir, force or recovery)
        dirty.unlink()
        return result
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description="Load complete CMS claims snapshots into Delta tables")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw/cms_synthetic_claims/extracted")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/lakehouse")
    parser.add_argument("--master", default="local[2]")
    parser.add_argument("--force", action="store_true", help="Reprocess unchanged files")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    spark = create_spark(args.master)
    try:
        run(spark, args.raw_dir, args.data_dir, args.force)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
