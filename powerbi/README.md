# Power BI

The local existing report is `dashboard/Health_Insurance_Claims_Dashboard.pbix`. It is preserved and ignored by Git. Its package contains a report layout and an embedded data model; the layout has one page named `Page 1`. Report refresh and rendering were not automated. The existing Excel workbook and dashboard screenshot remain under `excel/`.

The original `analytics.vw_ClaimOverview`, monthly, SLA, provider and review-queue views support the simulated operational dashboard. Approval, fraud, risk and leakage metrics are project-generated examples, not observed outcomes.

## New source-derived model

Use the SQL Server connector for the `lake` tables after the pipeline, export and SQL load complete. Azure SQL uses the same tables with an authenticated cloud connection.

- `lake.dim_date[DATE_KEY]` (one) -> `lake.fact_claim[DATE_KEY]` (many).
- `lake.dim_provider[PROVIDER_KEY]` (one) -> `lake.fact_claim[PRIMARY_PROVIDER_KEY]` (many).
- Use single-direction filtering from dimensions to the fact.
- Mark `dim_date[FULL_DATE]` as the date table and use it for service-start reporting.
- Monthly and provider summaries are standalone aggregate sources; do not join them to the fact in a way that multiplies values.

Example measures for a model table named `fact_claim`:

```dax
Claim Count = COUNTROWS(fact_claim)
CMS Claim Payment = SUM(fact_claim[CLAIM_PAYMENT_AMOUNT])
Average CMS Payment = DIVIDE([CMS Claim Payment], [Claim Count])
Claim Lines = SUM(fact_claim[LINE_COUNT])
```

Service-start month in the lakehouse differs from submission month in the simulated operations model. Keep those date definitions explicit in report labels. Provider attribution uses the lowest-numbered claim line and includes typed provider IDs; it is not a provider quality ranking.

Refresh imported data only after all pipeline stages succeed. For a file-based report, use `data/exports/gold` Parquet snapshots, never the raw files inside a Delta directory.
