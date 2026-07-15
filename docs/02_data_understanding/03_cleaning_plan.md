# Cleaning Plan

## Purpose

This document records the initial column-level cleaning decisions for the selected CMS synthetic claims datasets.

No columns have been removed at this stage.

## Decision Rules

- Critical identifiers and financial fields are retained.
- Constant columns are reviewed before removal.
- Columns with at least 95% missing values require detailed review.
- Sparse columns are not automatically deleted because they may apply only to particular claim types.
- Final cleaning decisions will be based on business relevance, data grain and source documentation.

## Summary

- beneficiary_2023 — KEEP_CRITICAL: 1 columns
- beneficiary_2023 — KEEP_INITIAL: 123 columns
- beneficiary_2023 — REVIEW_CONSTANT: 49 columns
- beneficiary_2023 — REVIEW_SPARSE: 12 columns
- carrier — KEEP_CRITICAL: 8 columns
- carrier — KEEP_INITIAL: 37 columns
- carrier — REVIEW_CONSTANT: 46 columns
- carrier — REVIEW_SPARSE: 5 columns
- inpatient — KEEP_CRITICAL: 8 columns
- inpatient — KEEP_INITIAL: 86 columns
- inpatient — REVIEW_CONSTANT: 84 columns
- inpatient — REVIEW_HIGH_MISSING: 12 columns
- inpatient — REVIEW_SPARSE: 7 columns
- outpatient — KEEP_CRITICAL: 8 columns
- outpatient — KEEP_INITIAL: 61 columns
- outpatient — REVIEW_CONSTANT: 87 columns
- outpatient — REVIEW_SPARSE: 6 columns

## Governance Rule

No raw source file will be modified. Cleaned outputs will be written to separate processed-data folders.