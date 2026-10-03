import csv
import hashlib
import re
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType


CLAIM_TYPES = ("carrier", "inpatient", "outpatient")
REQUIRED = {"BENE_ID", "CLM_ID", "CLM_FROM_DT", "CLM_THRU_DT", "CLM_PMT_AMT"}


def file_digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def read_claims(spark, path, claim_type, digest):
    if claim_type not in CLAIM_TYPES:
        raise ValueError(f"Unsupported claim type: {claim_type}")
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        columns = [name.strip().upper() for name in next(csv.reader(source, delimiter="|"))]
    if len(columns) != len(set(columns)) or any(
        not re.fullmatch(r"[A-Z][A-Z0-9_]*", name) for name in columns
    ):
        raise ValueError("Source column names must be unique identifiers")
    missing = REQUIRED - set(columns)
    line_column = "LINE_NUM" if claim_type == "carrier" else "CLM_LINE_NUM"
    if missing or line_column not in columns:
        raise ValueError(f"Missing required columns: {sorted(missing | ({line_column} - set(columns)))}")
    schema = StructType([StructField(name, StringType()) for name in columns])
    return (
        spark.read.schema(schema).option("header", True).option("sep", "|")
        .option("mode", "FAILFAST").option("encoding", "UTF-8")
        .csv(str(Path(path).resolve()))
        .withColumn("_source_file", F.lit(Path(path).name))
        .withColumn("_source_sha256", F.lit(digest))
        .withColumn("_ingested_at", F.current_timestamp())
    )
