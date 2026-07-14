# CMS Source Data Understanding

## Source

CMS Synthetic Medicare Enrollment, Fee-for-Service Claims and Prescription Drug Event Public Use Files.

## Source Type

Official public synthetic healthcare claims dataset.

## Geography

United States.

## Business Context

The dataset imitates Medicare enrollment and healthcare claims. It contains realistic but synthetic beneficiary and claim records and does not contain real patient information.

## Selected Source Files

### Beneficiary Files

Files:

- beneficiary_2015.csv to beneficiary_2025.csv

Grain:

- One row per beneficiary per year.

Primary key candidate:

- BENE_ID plus beneficiary year.

Usage:

- Member demographics
- Geography
- Enrollment status
- Chronic-condition indicators

### carrier.csv

Grain:

- One professional-service claim line.

Usage:

- Physician services
- Procedures
- Rendering-provider analysis
- Professional claim expenditure

### inpatient.csv

Grain:

- One inpatient claim line.

Usage:

- Hospital admissions
- Admission and discharge dates
- Length of stay
- Diagnosis and procedure analysis
- Inpatient payments

### outpatient.csv

Grain:

- One outpatient claim line.

Usage:

- Outpatient visits
- Procedures
- Diagnosis analysis
- Provider analysis
- Outpatient payments

## Important Relationships

BENE_ID links beneficiary records with claims.

CLM_ID identifies a medical claim.

A single CLM_ID can appear on multiple rows because one claim can contain multiple claim lines.

## Important Double-Counting Risk

Claim-level financial values may repeat across claim-line rows.

Before summing claim-level amounts, the data must first be reduced to one row per CLM_ID or handled using the correct claim-line amount field.

## File Delimiter

The CMS CSV files use the pipe character as the delimiter:

|

Python must read them using:

sep="|"

## Data-Provenance Category

Source fields from these files will be classified as:

SOURCE_SYNTHETIC_CMS

Operational fields generated later will be classified as:

PROJECT_SYNTHETIC

Calculated analytical fields will be classified as:

DERIVED

## Raw-Data Rules

- Never edit raw CSV files.
- Never overwrite downloaded files.
- Never open and resave raw files through Excel.
- Do not upload raw datasets to GitHub.
- Perform cleaning in separate processed files.
- Record every transformation.
- Never describe synthetic beneficiaries as real patients.

## Current File Inventory

The project currently contains:

- 11 beneficiary-year files
- carrier.csv
- inpatient.csv
- outpatient.csv

## Known Limitations

The data is synthetic and cannot support conclusions about actual Medicare beneficiaries.

The source does not contain the complete insurance-adjudication workflow.

Policy rules, claim decisions, denial reasons, work queues, adjusters, appeals, fraud alerts, overpayments and recoveries will be generated later and clearly documented.
