# SQL Server and Azure SQL

## Source-derived Gold tables

The new `lake` schema is separate from the original `stg`, `dim`, `fact` and `analytics` schemas.

1. Run `sql/schema/01_create_database_and_schemas.sql` to create the local database if needed.
2. In that database, run `sql/schema/05_create_lakehouse_tables.sql`.
3. Run `python -m src.pipeline`, then `python -m src.export_gold`.
4. Run `python -m src.load_gold_to_sql`.
5. Run `sql/analysis/03_lakehouse_analysis.sql` for source-derived monthly/provider results and reconciliation.

The export reads the current Delta snapshot, not every Parquet file in a Delta directory. Reading a Delta folder as ordinary Parquet can include obsolete versions and double-count data. The loader batches inserts, validates counts and financial totals, and commits the entire five-table refresh together. Errors roll back the refresh. Only `lake.*` is replaced.

The default connection uses Windows integrated authentication on `localhost`, database `HealthInsuranceClaimsDW`. Trusting the server certificate is limited to that local development default. Microsoft ODBC Driver 18 must be installed separately from `pyodbc`.

## Existing operational warehouse

The original full-refresh path remains:

1. `sql/schema/01_create_database_and_schemas.sql`
2. `sql/schema/02_create_star_schema_tables.sql`
3. `sql/schema/03_create_staging_table.sql`
4. `python -m src.transformations.load_claims_to_sql --reload`
5. `sql/etl/01_load_dimensions.sql`
6. `sql/etl/02_load_fact_claim.sql`
7. `sql/schema/04_create_analytical_indexes.sql`
8. `sql/views/01_create_analytical_views.sql`
9. `sql/analysis/02_create_reporting_procedures.sql`
10. `sql/validation/01_validate_star_schema.sql`

Without `--reload`, the Python loader only validates existing staging counts, unique keys and financial totals against its Parquet source. It no longer hard-codes 514,225 records. Reload is one transaction, with validation before commit. The fact load checks that dimension joins did not drop claims. The dimensional model and all simulated metrics are retained for the existing report.

## Azure connection boundary

No Azure resources were provisioned. Create/select an Azure SQL database through your own subscription, allow the client connection, install the ODBC driver, and set `CLAIMS_SQL_CONNECTION_STRING` in the process environment or secret store. For example, use Driver 18 with your server/database, `Authentication=ActiveDirectoryInteractive`, `Encrypt=yes` and `TrustServerCertificate=no`. Do not put passwords or tokens in this repository. Project code reads the environment directly; it does not automatically load `.env` files.

The new `05_create_lakehouse_tables.sql` and lakehouse analysis script operate in the selected database and do not use cross-database `USE` commands. They are the portable path for Azure SQL. The original SQL scripts target local SQL Server and contain `USE`, database creation and recovery settings; do not run the bootstrap unchanged against Azure SQL.

A Databricks extension would land source files in ADLS, use a runtime compatible with the Spark/Delta code, and publish Gold to the same SQL tables with approved credentials. The current command-line ingestion uses local `Path`/SHA-256 operations; an ADLS version needs storage-aware discovery and fingerprints. This repository does not claim that adaptation or deployment has been executed.
