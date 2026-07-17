# Day 3 — SQL and Data Modelling

## Database

- Database: HealthInsuranceClaimsDW
- Platform: Microsoft SQL Server
- Source: 514,225 synthetic claim records
- Grain: One row per unique claim

## Schemas

- stg — source staging tables
- dim — dimension tables
- fact — claim fact table
- analytics — reporting views and procedures
- audit — future ETL audit records

## Star Schema

### Fact table

- fact.Claim — 514,225 unique claims

### Dimension tables

- dim.Date
- dim.Beneficiary
- dim.Policy
- dim.Plan
- dim.Provider
- dim.ClaimStatus
- dim.DenialReason

## SQL Outputs

- Loaded Parquet data into SQL staging
- Loaded dimension and fact tables
- Created primary and foreign keys
- Added analytical indexes
- Created monthly, SLA, provider and review-queue views
- Created reusable reporting stored procedures
- Wrote claims business-analysis queries

## Validation Results

- Staging rows: 514,225
- Fact rows: 514,225
- Unique claim keys: 514,225
- Duplicate claim keys: 0
- Financial hierarchy errors: 0
- Missing mandatory dimension keys: 0
- Star-schema validation: PASS

## Business Analysis Supported

- Approval and rejection rates
- Claims volume and expenditure trends
- SLA breaches and turnaround time
- Provider performance
- Suspicious-claim indicators
- Estimated financial leakage
- Human-review prioritisation