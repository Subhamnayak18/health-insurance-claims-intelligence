# Raw Data Profile Summary

## Purpose

This report documents the initial structure and quality of the selected CMS synthetic claims files. No raw source files were modified.

## Dataset Results

### beneficiary_2023

- Source file: `beneficiary_2023.csv`
- Total rows: 9,179
- Number of columns: 185
- Sample rows profiled: 5,000
- Exact duplicate rows in sample: 0
- `BENE_ID` available: True
- `CLM_ID` available: False

### carrier

- Source file: `carrier.csv`
- Total rows: 1,121,004
- Number of columns: 96
- Sample rows profiled: 5,000
- Exact duplicate rows in sample: 0
- `BENE_ID` available: True
- `CLM_ID` available: True

### inpatient

- Source file: `inpatient.csv`
- Total rows: 58,066
- Number of columns: 197
- Sample rows profiled: 5,000
- Exact duplicate rows in sample: 0
- `BENE_ID` available: True
- `CLM_ID` available: True

### outpatient

- Source file: `outpatient.csv`
- Total rows: 575,092
- Number of columns: 162
- Sample rows profiled: 5,000
- Exact duplicate rows in sample: 0
- `BENE_ID` available: True
- `CLM_ID` available: True

## Interpretation

- Repeated claim IDs may represent valid claim lines.
- Exact duplicate rows require separate investigation.
- Claim-header amounts may repeat across claim-line records.
- Missing values are not automatically data-quality errors because some fields apply only to specific claim types.

## Status

This profiling stage is descriptive only. No records or columns have been removed.