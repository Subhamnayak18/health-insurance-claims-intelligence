import os
import sys
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


ROOT = Path(__file__).resolve().parents[2]


def create_spark(master="local[2]"):
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    local = ROOT / ".spark-local"
    local.mkdir(exist_ok=True)
    builder = (
        SparkSession.builder.appName("claims-medallion")
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.ansi.enabled", "true")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.databricks.delta.snapshotPartitions", "4")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.jars.ivy", str(local / "ivy"))
        .config("spark.local.dir", str(local / "tmp"))
        .config("spark.sql.warehouse.dir", (local / "warehouse").as_uri())
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
