# Original dataset research

Historical selection notes. Only the CMS synthetic claims and beneficiary files are present; external benchmarking and modelling datasets below were proposals, not implemented integrations.

## Geography Decision

Selected geography: United States.

Selected business context: Medicare-style fee-for-service health-insurance claims.

## Reason for Selection

The United States provides stronger official public resources for:

* Beneficiary data.
* Claim and claim-line structures.
* Diagnosis and procedure codes.
* Provider identifiers.
* Service utilisation.
* Submitted charges and payment amounts.
* Relational data modelling.
* Provider benchmarking.
* Machine-learning feature engineering.

Indian official sources such as PM-JAY and IRDAI remain highly relevant, but comparable public claim-level operational datasets are difficult to obtain. An India-focused implementation would therefore require most of the transaction-level data to be generated synthetically.

## Selected Primary Dataset

CMS Synthetic Medicare Enrollment, Fee-for-Service Claims and Prescription Drug Event Public Use Files.

## Selected Files for Initial Evaluation

* Beneficiary files.
* Inpatient claims.
* Outpatient claims.
* Carrier claims.
* Prescription drug events where relevant.

The final selection will be confirmed after raw-data profiling.

## Supporting Dataset

CMS Medicare Physician and Other Practitioners by Provider and Service.

This source will support:

* Provider peer benchmarking.
* Service-level utilisation analysis.
* Charge and payment comparisons.
* Geographic provider analysis.

## Optional Fraud Benchmark

Healthcare Provider Fraud Detection Analysis.

This dataset may be used only as a modelling benchmark. It will not automatically be merged with the primary dataset.

## Data Limitations

The CMS claim-level dataset is synthetic and must not be presented as real patient-level information.

The project will not use the dataset to make population-level clinical or policy conclusions.

The source does not contain the complete adjudication and operational workflow required for the project.

## Synthetic Data Requirements

The project will generate data for:

* Policies and plan rules.
* Claim submissions.
* Required documents.
* Pre-authorisations.
* Adjudication decisions.
* Claim adjustments.
* Denial reasons.
* Adjusters and work queues.
* Operational tasks.
* Payment-processing events.
* Appeals.
* Fraud alerts.
* Overpayments.
* Recoveries.

## Data Provenance Categories

* SOURCE_SYNTHETIC_CMS
* SOURCE_REAL_AGGREGATE_CMS
* PROJECT_SYNTHETIC
* DERIVED
* ASSUMED_REFERENCE

## Final Recommendation

Use official CMS synthetic claims as the main relational source, supplement them with real CMS provider aggregates and generate only the operational fields that are unavailable publicly.
