from datetime import date
from decimal import Decimal

from pyspark.sql import functions as F

from src.quality.claims import validate_lines
from src.transformations.spark_claims import build_claim_headers, build_gold, clean_claim_lines


def source(spark, overrides=None):
    row = {"BENE_ID": " member-1 ", "CLM_ID": "001", "CLM_FROM_DT": "01-Jan-2023",
           "CLM_THRU_DT": "2023-01-02", "CLM_PMT_AMT": "100.00", "LINE_NUM": "1",
           "ORG_NPI_NUM": "0012345678", "NCH_CARR_CLM_SBMTD_CHRG_AMT": "140.00",
           "LINE_NCH_PMT_AMT": "60.00", "HCPCS_CD": " N/A "}
    row.update(overrides or {})
    return spark.createDataFrame([row])


def test_header_grain_dedup_and_source_mappings(spark):
    first = source(spark)
    second = source(spark, {"LINE_NUM": "2", "LINE_NCH_PMT_AMT": "40.00"})
    lines = clean_claim_lines(first.unionByName(first).unionByName(second), "carrier")
    assert lines.count() == 2
    counts, _ = validate_lines(lines)
    assert counts["invalid_rows"] == counts["conflicting_line_keys"] == counts["conflicting_claim_headers"] == 0
    headers = build_claim_headers(lines)
    row = headers.first()
    assert row.CLAIM_PAYMENT_AMOUNT == Decimal("100.00")
    assert row.LINE_PAYMENT_AMOUNT == Decimal("100.00")
    assert row.CLAIM_TOTAL_CHARGE_AMOUNT == Decimal("140.00")
    assert row.PRIMARY_PROVIDER_KEY == "NPI:0012345678"
    assert row.BENE_ID == "member-1"
    assert row.CLAIM_FROM_DATE == date(2023, 1, 1)
    assert row.PRIMARY_PROCEDURE_CODE is None
    assert row.LINE_COUNT == 2 and row.SERVICE_DAYS == 2
    assert build_gold(headers, lines)["dim_date"].count() == 2


def test_invalid_types_and_missing_values_are_reported(spark):
    bad = source(spark, {"CLM_FROM_DT": "31-Feb-2023", "CLM_PMT_AMT": "NaN", "LINE_NUM": "1.5", "BENE_ID": " NULL "})
    errors = clean_claim_lines(bad, "carrier").first()._errors
    assert {"invalid_from_date", "missing_claim_payment", "invalid_line_number", "missing_beneficiary"} <= set(errors)
    precision = clean_claim_lines(source(spark, {"CLM_PMT_AMT": "1.234"}), "carrier").first()
    assert "invalid_claim_payment_amount" in precision._errors


def test_conflicting_duplicates_and_headers_fail(spark):
    duplicate = source(spark).unionByName(source(spark, {"CLM_PMT_AMT": "200.00"}))
    counts, _ = validate_lines(clean_claim_lines(duplicate, "carrier"))
    assert counts["conflicting_line_keys"] == 1
    assert counts["conflicting_claim_headers"] == 1


def test_negative_adjustments_are_retained(spark):
    lines = clean_claim_lines(source(spark, {"CLM_PMT_AMT": "-12.50"}), "carrier")
    assert lines.first()._errors == []
    assert lines.first().NEGATIVE_PAYMENT_FLAG
    assert build_claim_headers(lines).first().CLAIM_PAYMENT_AMOUNT == Decimal("-12.50")


def test_reversed_dates_fail(spark):
    errors = clean_claim_lines(source(spark, {"CLM_THRU_DT": "2022-12-01"}), "carrier").first()._errors
    assert "reversed_dates" in errors
