# Synthetic Claim Operations

## Purpose

CMS provides claim and payment structures but does not contain the complete internal adjudication workflow.

This dataset adds documented project-generated operational fields.

## Final Grain

One row per `CLAIM_KEY`.

## Generated Information

- Policy and plan assignment
- Claim submission and decision dates
- Documentation and pre-authorisation status
- Claim status and denial reason
- Financial adjustments
- SLA and turnaround-time indicators
- Manual-review and fraud indicators
- Work queue, priority and adjuster assignment

## Status Distribution

- APPROVED: 343,974
- MANUAL_REVIEW: 27,097
- PARTIALLY_APPROVED: 60,171
- PENDING: 44,311
- REJECTED: 38,672

## Financial Control

`BILLED_AMOUNT >= ELIGIBLE_AMOUNT >= APPROVED_AMOUNT >= PAID_AMOUNT`

## Governance

All workflow and adjudication fields are classified as `PROJECT_SYNTHETIC`.

Synthetic claim decisions are created for portfolio analysis and do not represent real insurance decisions.