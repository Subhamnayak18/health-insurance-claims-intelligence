from decimal import Decimal

import numpy as np
import pandas as pd

from src.data_cleaning.clean_cms_data import remove_exact_duplicates
from src.transformations.load_claims_to_sql import clean_value, validate_sql_data
from src.transformations.build_claim_header import coalesce_columns


def test_legacy_chunk_dedup():
    seen = set()
    first, removed = remove_exact_duplicates(pd.DataFrame({"id": ["a", "a", "b"]}), seen)
    assert len(first) == 2 and removed == 1
    second, removed = remove_exact_duplicates(pd.DataFrame({"id": ["b", "c"]}), seen)
    assert len(second) == 1 and removed == 1


def test_odbc_value_conversion():
    assert clean_value(pd.NA) is None
    assert clean_value(np.int64(7)) == 7
    assert clean_value(Decimal("1.20")) == Decimal("1.20")


def test_coalesce_does_not_copy_codes_between_rows():
    data = pd.DataFrame({"HCPCS_CD": pd.Series([None, "99495", None], dtype="string")})
    result = coalesce_columns(data, ["HCPCS_CD", "ICD_PRCDR_CD1"])
    assert result.isna().tolist() == [True, False, True]
    data["ICD_PRCDR_CD1"] = pd.Series(["fallback", "unused", None], dtype="string")
    result = coalesce_columns(data, ["HCPCS_CD", "ICD_PRCDR_CD1"])
    assert result.iloc[0] == "fallback" and result.iloc[1] == "99495"
    assert pd.isna(result.iloc[2])


def test_staging_validation_uses_source_count_and_totals(tmp_path):
    source = tmp_path / "operations.parquet"
    pd.DataFrame({"CLAIM_KEY": ["a"], "BILLED_AMOUNT": [20.1], "APPROVED_AMOUNT": [12.0], "PAID_AMOUNT": [10.0]}).to_parquet(source)

    class Cursor:
        def execute(self, query):
            return self

        def fetchone(self):
            return (1, 1, Decimal("20.10"), Decimal("12.00"), Decimal("10.00"))

    validate_sql_data(Cursor(), source)
