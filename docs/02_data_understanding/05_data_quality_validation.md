# Data Quality Validation

## Purpose

This report validates beneficiary and claim relationships after cleaning.

## Validation Results

- **beneficiary_history — DUPLICATE_BENEFICIARY_YEAR_KEY:** PASS (0 failed rows)
- **carrier — MISSING_BENE_ID:** PASS (0 failed rows)
- **carrier — MISSING_CLM_ID:** PASS (0 failed rows)
- **carrier — INVALID_FROM_DATE:** PASS (0 failed rows)
- **carrier — INVALID_THROUGH_DATE:** PASS (0 failed rows)
- **carrier — CLAIM_DATE_ORDER:** PASS (0 failed rows)
- **carrier — NEGATIVE_PAYMENT_AMOUNT:** PASS (0 failed rows)
- **carrier — DUPLICATE_CLAIM_LINE_KEY:** PASS (0 failed rows)
- **carrier — UNMATCHED_BENEFICIARY_YEAR:** PASS (0 failed rows)
- **inpatient — MISSING_BENE_ID:** PASS (0 failed rows)
- **inpatient — MISSING_CLM_ID:** PASS (0 failed rows)
- **inpatient — INVALID_FROM_DATE:** PASS (0 failed rows)
- **inpatient — INVALID_THROUGH_DATE:** PASS (0 failed rows)
- **inpatient — CLAIM_DATE_ORDER:** PASS (0 failed rows)
- **inpatient — NEGATIVE_PAYMENT_AMOUNT:** PASS (0 failed rows)
- **inpatient — DUPLICATE_CLAIM_LINE_KEY:** PASS (0 failed rows)
- **inpatient — UNMATCHED_BENEFICIARY_YEAR:** PASS (0 failed rows)
- **outpatient — MISSING_BENE_ID:** PASS (0 failed rows)
- **outpatient — MISSING_CLM_ID:** PASS (0 failed rows)
- **outpatient — INVALID_FROM_DATE:** PASS (0 failed rows)
- **outpatient — INVALID_THROUGH_DATE:** PASS (0 failed rows)
- **outpatient — CLAIM_DATE_ORDER:** PASS (0 failed rows)
- **outpatient — NEGATIVE_PAYMENT_AMOUNT:** PASS (0 failed rows)
- **outpatient — DUPLICATE_CLAIM_LINE_KEY:** PASS (0 failed rows)
- **outpatient — UNMATCHED_BENEFICIARY_YEAR:** PASS (0 failed rows)

## Interpretation

- `PASS` means no exceptions were found.
- `WARNING` means the records require business review.
- `FAIL` means a critical data-quality rule was violated.
- Negative payments are not automatically deleted because they may represent legitimate claim reversals or adjustments.