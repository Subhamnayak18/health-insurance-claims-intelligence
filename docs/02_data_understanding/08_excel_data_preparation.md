# Excel Data Preparation

## Purpose

This step prepares business-friendly source files for Excel.

## Files

- Full Power Query source: `claim_operations_full.csv`
- Worksheet sample: `claim_operations_sample.csv`
- Full rows: 514,225
- Sample rows: 50,000

## Excel Loading Strategy

- Load the full claim file through Power Query.
- Load the full file to the Data Model rather than directly to a worksheet.
- Use the 50,000-row sample for formulas, manual checks and demonstrations.
- Use the lookup tables for XLOOKUP and business descriptions.

## Important Control

The sample is proportionally selected across claim type and claim status.

## Data Provenance

The exported workflow fields remain classified as `PROJECT_SYNTHETIC`.