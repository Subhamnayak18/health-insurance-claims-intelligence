from delta.tables import DeltaTable


def write_delta(df, path):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(str(path))


def merge_snapshot(df, path, keys):
    """Upsert one complete snapshot; remove keys absent from that snapshot."""
    spark = df.sparkSession
    if not DeltaTable.isDeltaTable(spark, str(path)):
        write_delta(df, path)
        return
    target = DeltaTable.forPath(spark, str(path))
    incoming = {field.name: field.dataType for field in df.schema}
    for field in target.toDF().schema:
        if field.name not in incoming or incoming[field.name] != field.dataType:
            raise ValueError(f"Breaking Silver schema change: {field.name}")
    condition = " AND ".join(f"t.`{key}` = s.`{key}`" for key in keys)
    (target.alias("t").merge(df.alias("s"), condition).withSchemaEvolution()
     .whenMatchedUpdateAll()
     .whenNotMatchedInsertAll().whenNotMatchedBySourceDelete().execute())
