# Architecture and data contracts

The lakehouse extends the original project without replacing its operational simulation or report files.

## Tables

| Layer/table | Grain | Key |
| --- | --- | --- |
| Bronze: carrier, inpatient, outpatient | Source record | Source file fingerprint and retained source fields |
| Silver: carrier, inpatient, outpatient | Valid claim line | CLAIM_KEY + LINE_NUMBER |
| Gold: fact_claim | Claim | CLAIM_TYPE + CLAIM_ID, represented by CLAIM_KEY |
| Gold: dim_provider | Typed provider identifier | PROVIDER_KEY |
| Gold: dim_date | Calendar day, continuous across the claims range | DATE_KEY |
| Gold: monthly_claims | Service-start month and claim type | CLAIM_MONTH + CLAIM_TYPE |
| Gold: provider_claims | Representative provider and claim type | PRIMARY_PROVIDER_KEY + CLAIM_TYPE |

Bronze retains all source columns as strings plus the filename, SHA-256 and ingestion timestamp. Delta versions preserve previous snapshots until explicitly vacuumed; the pipeline does not vacuum tables. Original CSV files remain untouched.

Silver trims strings and normalizes blank/NULL/NA/N/A/None values. It retains source fields alongside parsed dates and decimal amounts. Exact duplicates are removed across all normalized source fields, before business-key checks. Invalid required fields, malformed money, conflicting line keys, or inconsistent header values stop that source before its Silver MERGE. Quarantine tables retain the invalid rows or conflicting keys. Missing providers and negative payments are warnings; neither is silently discarded.

Gold counts the repeated CLM_PMT_AMT once per claim. Line payment and charge amounts are summed separately; unavailable amounts remain null. Carrier charge uses NCH_CARR_CLM_SBMTD_CHRG_AMT and outpatient line payment uses REV_CNTR_PMT_AMT_AMT, two fields omitted by the original header mapping. The original pandas outputs are preserved as historical results.

The lowest line number supplies the representative provider, procedure and diagnosis. Provider totals attribute the whole claim to that representative; they do not allocate money among all treating providers. A provider key includes its identifier type (PRVDR_NUM or NPI), preserving leading zeros and avoiding cross-namespace collisions. No provider names, specialties or geography are invented. Beneficiaries remain a natural identifier on the new fact; the existing beneficiary-year validation remains available in the pandas path.

## Incremental processing

Each source filename represents a **complete current snapshot** of one claim type. File hashes in `state/claims.json` determine which files need processing. Changed inputs overwrite the current Bronze snapshot and MERGE into their Silver table. Existing line keys update, new keys insert, and absent keys delete. Full-snapshot semantics make removed lines and corrections explicit; never put a partial extract under these filenames.

Gold is rebuilt from all three Silver tables after validation and line-count reconciliation. This avoids incorrect additive aggregates when an existing claim changes. Additive source columns pass through Bronze and Silver via scoped Delta schema evolution. Dropping a previous Silver column or changing its type raises an error. Curated Gold schemas are explicit.

`--force` reprocesses all snapshots after code changes. A hash is a file-change detector, not an event-time watermark or CDC implementation. The pipeline scans changed files in full and is intended for the supplied local dataset.

## Failure and recovery

The run takes an exclusive `state/writer.lock`. It writes `state/incomplete` before changing tables and removes it only after Gold and the state file succeed. Exports refuse incomplete runs. A failed run leaves the marker and can be retried with the same command; recovery reprocesses all source snapshots. The successful state file is replaced atomically.

Each Delta table commit is atomic; publication across several tables is not. A failed run may have newer Bronze/Silver tables or partially refreshed Gold. Read Gold only after the run succeeds; the SQL loader publishes all exported Gold tables in one database transaction. Do not overlap pipeline, export, or SQL publication. If a process is forcibly killed, confirm no writer remains before removing a stale `writer.lock` and rerunning.

No cloud storage, job scheduler, streaming ingestion, event-time CDC or Databricks deployment was provisioned. See the Azure connection notes for the extension boundary.
