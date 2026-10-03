# Raw Data

Place original downloaded source files here. The pipeline expects pipe-delimited `carrier.csv`, `inpatient.csv` and `outpatient.csv` under `cms_synthetic_claims/extracted/`. The retained pandas beneficiary validation also uses `beneficiary_2015.csv` through `beneficiary_2025.csv` in that directory.

Source: [CMS Synthetic Medicare collection](https://data.cms.gov/collection/synthetic-medicare-enrollment-fee-for-service-claims-and-prescription-drug-event). Extract downloaded archives without resaving the CSVs. All three claims inputs must be complete snapshots. For a small run without downloading data, use the hand-written fixtures documented in the root README.

Rules:

- Do not manually edit raw source files.
- Preserve original file names.
- Record every source in the data-source register.
- Do not commit large raw datasets to GitHub.
- Do not place credentials or connection strings here.
