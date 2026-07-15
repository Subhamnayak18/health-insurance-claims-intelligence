# Unified Claim Header Build

## Purpose

The CMS source files are stored at claim-line grain. This transformation creates one record per claim.

## Double-Counting Control

- `CLM_PMT_AMT` is treated as a claim-level value.
- Claim-level payment is selected once per claim.
- Line-level submitted, allowed and payment amounts are summed.
- `CLAIM_TYPE` and `CLAIM_ID` form the unique claim key.

## Results

### carrier

- Source claim lines: 1,121,004
- Claim-header rows: 90,705
- Unique claim keys: 90,705
- Reconciled line count: 1,121,004

### inpatient

- Source claim lines: 58,066
- Claim-header rows: 20,867
- Unique claim keys: 20,867
- Reconciled line count: 58,066

### outpatient

- Source claim lines: 575,092
- Claim-header rows: 402,653
- Unique claim keys: 402,653
- Reconciled line count: 575,092

## Final Grain

One row per `CLAIM_TYPE` and `CLAIM_ID`.