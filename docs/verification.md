# Verification

The upgrade was executed locally against the supplied CMS files and the existing SQL Server database. Machine-readable counts, source hashes and reconciliation results are in `data/metadata/lakehouse_verification.json`.

## Lakehouse

- Processed all 1,754,162 source claim lines into 514,225 claim headers.
- Reconciled every claim key, line count and claim payment against the original header Parquet.
- Total claim payment: 999,076,318.08. This is a synthetic source total, not business savings or measured impact.
- No exact duplicate rows, invalid required values, conflicting line keys or conflicting header fields were found in these three source snapshots.
- Produced 2,928 continuous calendar dates, 13,136 typed provider identifiers, 292 month/type summaries and 14,810 representative-provider/type summaries.
- Verified unique fact keys, dimension relationships, date coverage and unchanged-input replay without rewriting Gold versions.
- Exported current Delta snapshots to Parquet and loaded all five `lake` tables into local SQL Server. SQL counts and payment totals reconcile with Gold.

## Tests and existing functionality

All 12 automated tests passed across the transformation/Delta suite, end-to-end integration test and legacy regression tests. They cover typed cleaning, null handling, exact and conflicting duplicates, payment grain, negative adjustments, date validation, source schema checks, Delta insert/update/delete, additive schema evolution, rejected schema removal, unchanged replay, corrected snapshots, quarantine, recovery and exports. Legacy tests cover chunk deduplication, ODBC values, source-based SQL validation and per-row field fallback.

The original pandas cleaning and beneficiary validation were rerun into an isolated verification directory. The legacy header build reproduced the saved original exactly after correcting per-row fallback. The original `bfill(axis=1)` could copy a procedure code between rows for a single-column pandas 2.2.3 frame; explicit Series fallback prevents that. The seeded operational dataset was reproduced exactly after normalizing timestamp precision for comparison. Full Excel-source exports and the 50,000-row sample were regenerated successfully. Original processed datasets, Excel files and the Power BI file are preserved.

The staging loader was exercised on all 514,225 records and validated before rollback. Existing table/index scripts, dimension and fact loads, analytical views, stored procedures and business queries were executed inside a rolled-back transaction. The corrected SQL validation passed. The original warehouse still contains its 514,225 claims. Only the separate `lake` schema was created and populated permanently.

The dependency set passed `uv pip check`. Python 3.11.15, Java 17, PySpark 3.5.6 and Delta 3.3.2 were used for successful Spark execution. The bundled Python 3.12 runtime crashed in Windows Spark workers, so it is not the documented runtime. Windows Spark emitted temporary-JAR cleanup warnings after successful jobs; temporary files were removed after the JVM exited.

## Not executed

- Azure SQL, ADLS and Databricks deployment: no cloud resources or credentials were supplied. Azure connection instructions are documented separately.
- Power BI Desktop refresh, DAX execution and report rendering: the existing PBIX package was inspected and preserved; the new relationships/measures are documented, not claimed as applied to that report.
- GitHub Actions results are tracked separately in the [workflow runs](https://github.com/Subhamnayak18/health-insurance-claims-intelligence/actions/workflows/tests.yml); the evidence above records local execution.

All dataset counts describe these supplied snapshots. The project does not claim streaming ingestion, deployment benchmarks, fraud-model accuracy, financial savings or real patient outcomes.
