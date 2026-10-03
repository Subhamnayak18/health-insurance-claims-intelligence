from pyspark.sql import functions as F


MONEY_FIELDS = {
    "CLAIM_PAYMENT_AMOUNT": ["CLM_PMT_AMT"],
    "CLAIM_TOTAL_CHARGE_AMOUNT": ["CLM_TOT_CHRG_AMT", "NCH_CARR_CLM_SBMTD_CHRG_AMT", "CLM_SBMTD_CHRG_AMT"],
    "LINE_SUBMITTED_CHARGE_AMOUNT": ["LINE_SBMTD_CHRG_AMT", "REV_CNTR_TOT_CHRG_AMT"],
    "LINE_ALLOWED_AMOUNT": ["LINE_ALOWD_CHRG_AMT"],
    "LINE_PAYMENT_AMOUNT": ["LINE_NCH_PMT_AMT", "REV_CNTR_PMT_AMT_AMT", "REV_CNTR_PMT_AMT"],
}


def coalesce_fields(df, names):
    available = [F.col(name) for name in names if name in df.columns]
    return F.coalesce(*available) if available else F.lit(None).cast("string")


def normalize_strings(df):
    return df.select(*[
        F.when(F.upper(F.trim(F.col(name))).isin("", "NULL", "NA", "N/A", "NONE"), None)
        .otherwise(F.trim(F.col(name))).alias(name)
        if not name.startswith("_") else F.col(name)
        for name in df.columns
    ])


def parse_date(name):
    return F.coalesce(
        F.try_to_timestamp(F.col(name), F.lit("dd-MMM-yyyy")),
        F.try_to_timestamp(F.col(name), F.lit("yyyy-MM-dd")),
    ).cast("date")


def clean_claim_lines(bronze, claim_type):
    normalized = normalize_strings(bronze)
    source_columns = [name for name in normalized.columns if not name.startswith("_")]
    lines = normalized.dropDuplicates(source_columns)
    # Fingerprint all source fields, including optional columns, for row lineage.
    lines = lines.withColumn("_row_hash", F.sha2(F.to_json(F.struct(*[
        F.col(name) for name in sorted(source_columns)
    ]), {"ignoreNullFields": "false"}), 256))
    lines = (lines.withColumn("CLAIM_TYPE", F.lit(claim_type.upper()))
             .withColumn("CLAIM_ID", F.col("CLM_ID"))
             .withColumn("CLAIM_KEY", F.concat_ws("-", "CLAIM_TYPE", "CLM_ID"))
             .withColumn("CLAIM_FROM_DATE", parse_date("CLM_FROM_DT"))
             .withColumn("CLAIM_THRU_DATE", parse_date("CLM_THRU_DT")))
    line_name = "LINE_NUM" if claim_type == "carrier" else "CLM_LINE_NUM"
    lines = lines.withColumn("LINE_NUMBER", F.expr(f"try_cast({line_name} as int)"))
    errors = [
        F.when(F.col("BENE_ID").isNull(), "missing_beneficiary"),
        F.when(F.col("CLM_ID").isNull(), "missing_claim_id"),
        F.when(F.col("LINE_NUMBER").isNull() | (F.col("LINE_NUMBER") <= 0), "invalid_line_number"),
        F.when(F.col("CLAIM_FROM_DATE").isNull(), "invalid_from_date"),
        F.when(F.col("CLAIM_THRU_DATE").isNull(), "invalid_thru_date"),
        F.when(F.col("CLAIM_FROM_DATE") > F.col("CLAIM_THRU_DATE"), "reversed_dates"),
    ]
    for target, candidates in MONEY_FIELDS.items():
        raw_name = f"_raw_{target}"
        lines = lines.withColumn(raw_name, coalesce_fields(lines, candidates))
        # Reject extra precision rather than silently rounding source money.
        lines = lines.withColumn(target, F.when(
            F.col(raw_name).rlike(r"^[+-]?\d+(\.\d{1,2})?$"),
            F.expr(f"try_cast({raw_name} as decimal(18,2))"),
        ))
        errors.append(F.when(F.col(raw_name).isNotNull() & F.col(target).isNull(), f"invalid_{target.lower()}"))
    errors.append(F.when(F.col("CLAIM_PAYMENT_AMOUNT").isNull(), "missing_claim_payment"))
    provider_fields = [name for name in ["PRVDR_NUM", "ORG_NPI_NUM", "PRF_PHYSN_NPI", "RNDRNG_PHYSN_NPI", "AT_PHYSN_NPI"] if name in lines.columns]
    lines = (lines.withColumn("PROVIDER_ID", coalesce_fields(lines, provider_fields))
             .withColumn("PROVIDER_ID_TYPE", F.coalesce(*[
                 F.when(F.col(name).isNotNull(), F.lit("PRVDR_NUM" if name == "PRVDR_NUM" else "NPI"))
                 for name in provider_fields
             ], F.lit("UNKNOWN")))
             .withColumn("PROVIDER_KEY", F.when(F.col("PROVIDER_ID").isNotNull(),
                 F.concat_ws(":", "PROVIDER_ID_TYPE", "PROVIDER_ID")).otherwise("UNKNOWN"))
             .withColumn("PROCEDURE_CODE", coalesce_fields(lines, ["HCPCS_CD", "ICD_PRCDR_CD1"]))
             .withColumn("DIAGNOSIS_CODE", coalesce_fields(lines, ["PRNCPAL_DGNS_CD", "ICD_DGNS_CD1", "LINE_ICD_DGNS_CD"]))
             .withColumn("_errors", F.filter(F.array(*errors), lambda value: value.isNotNull()))
             .withColumn("NEGATIVE_PAYMENT_FLAG", F.col("CLAIM_PAYMENT_AMOUNT") < 0))
    return lines.drop(*[f"_raw_{name}" for name in MONEY_FIELDS])


def build_claim_headers(lines):
    # Header fields must pass consistency checks before this aggregation.
    representative = F.min(F.struct(
        "LINE_NUMBER", "PROVIDER_KEY", "PROVIDER_ID", "PROVIDER_ID_TYPE", "PROCEDURE_CODE", "DIAGNOSIS_CODE"
    )).alias("first_line")
    headers = lines.groupBy("CLAIM_TYPE", "CLAIM_ID", "CLAIM_KEY").agg(
        F.min("BENE_ID").alias("BENE_ID"),
        F.min("CLAIM_FROM_DATE").alias("CLAIM_FROM_DATE"),
        F.max("CLAIM_THRU_DATE").alias("CLAIM_THRU_DATE"),
        F.max("CLAIM_PAYMENT_AMOUNT").alias("CLAIM_PAYMENT_AMOUNT"),
        F.max("CLAIM_TOTAL_CHARGE_AMOUNT").alias("CLAIM_TOTAL_CHARGE_AMOUNT"),
        F.count("*").alias("LINE_COUNT"),
        F.countDistinct("PROVIDER_KEY").alias("UNIQUE_PROVIDER_COUNT"),
        F.countDistinct("PROCEDURE_CODE").alias("UNIQUE_PROCEDURE_COUNT"),
        *[F.sum(name).alias(name) for name in ["LINE_SUBMITTED_CHARGE_AMOUNT", "LINE_ALLOWED_AMOUNT", "LINE_PAYMENT_AMOUNT"]],
        representative,
    )
    return (headers
            .withColumn("PRIMARY_PROVIDER_KEY", F.col("first_line.PROVIDER_KEY"))
            .withColumn("PRIMARY_PROVIDER_ID", F.col("first_line.PROVIDER_ID"))
            .withColumn("PRIMARY_PROCEDURE_CODE", F.col("first_line.PROCEDURE_CODE"))
            .withColumn("PRIMARY_DIAGNOSIS_CODE", F.col("first_line.DIAGNOSIS_CODE"))
            .withColumn("CLAIM_YEAR", F.year("CLAIM_FROM_DATE"))
            .withColumn("CLAIM_MONTH", F.date_format("CLAIM_FROM_DATE", "yyyy-MM"))
            .withColumn("SERVICE_DAYS", F.datediff("CLAIM_THRU_DATE", "CLAIM_FROM_DATE") + 1)
            .withColumn("DATE_KEY", F.date_format("CLAIM_FROM_DATE", "yyyyMMdd").cast("int"))
            .withColumn("DATA_PROVENANCE", F.lit("DERIVED_FROM_SOURCE_SYNTHETIC_CMS"))
            .drop("first_line"))


def build_gold(headers, lines):
    dates = headers.agg(F.min("CLAIM_FROM_DATE").alias("start"), F.max("CLAIM_THRU_DATE").alias("end"))
    dates = dates.select(F.explode(F.sequence("start", "end")).alias("FULL_DATE"))
    dates = (dates.withColumn("DATE_KEY", F.date_format("FULL_DATE", "yyyyMMdd").cast("int"))
             .withColumn("CALENDAR_YEAR", F.year("FULL_DATE"))
             .withColumn("CALENDAR_MONTH", F.month("FULL_DATE"))
             .withColumn("YEAR_MONTH", F.date_format("FULL_DATE", "yyyy-MM")))
    providers = lines.select("PROVIDER_KEY", "PROVIDER_ID", "PROVIDER_ID_TYPE").distinct()
    monthly = headers.groupBy("CLAIM_MONTH", "CLAIM_TYPE").agg(
        F.count("*").alias("CLAIM_COUNT"), F.sum("LINE_COUNT").alias("LINE_COUNT"),
        F.sum("CLAIM_PAYMENT_AMOUNT").alias("CLAIM_PAYMENT_AMOUNT"),
        F.sum("CLAIM_TOTAL_CHARGE_AMOUNT").alias("CLAIM_TOTAL_CHARGE_AMOUNT"),
    )
    provider_summary = headers.groupBy("PRIMARY_PROVIDER_KEY", "CLAIM_TYPE").agg(
        F.count("*").alias("CLAIM_COUNT"),
        F.sum("CLAIM_PAYMENT_AMOUNT").alias("CLAIM_PAYMENT_AMOUNT"),
    )
    return {"fact_claim": headers, "dim_provider": providers, "dim_date": dates,
            "monthly_claims": monthly, "provider_claims": provider_summary}
