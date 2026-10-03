from functools import reduce
from operator import or_

from pyspark.sql import functions as F


def validate_lines(lines):
    row_errors = lines.filter(F.size("_errors") > 0)
    duplicates = lines.groupBy("CLAIM_KEY", "LINE_NUMBER").count().filter("count > 1")
    header_fields = ["BENE_ID", "CLAIM_FROM_DATE", "CLAIM_THRU_DATE", "CLAIM_PAYMENT_AMOUNT", "CLAIM_TOTAL_CHARGE_AMOUNT"]
    conflicts = lines.groupBy("CLAIM_KEY").agg(*[
        F.countDistinct(name).alias(name) for name in header_fields
    ]).filter(reduce(or_, [F.col(name) > 1 for name in header_fields]))
    counts = {
        "invalid_rows": row_errors.count(),
        "conflicting_line_keys": duplicates.count(),
        "conflicting_claim_headers": conflicts.count(),
        "negative_payment_lines": lines.filter("NEGATIVE_PAYMENT_FLAG").count(),
        "missing_provider_lines": lines.filter("PROVIDER_ID IS NULL").count(),
    }
    return counts, {"invalid_rows": row_errors, "conflicting_line_keys": duplicates,
                    "conflicting_claim_headers": conflicts}
