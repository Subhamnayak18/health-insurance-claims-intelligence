# Original project proposal

Historical planning document. Implemented scope and verified results are in the repository README and docs/verification.md. Forecasting, ML models, Snowflake, appeals/recovery processing and cloud deployment in this proposal were not implemented.

## Project Title

Health Insurance Claims Intelligence & Adjudication Platform

## Business Context

A health insurer processes claims submitted by healthcare providers and insured members. Claims must be checked for member eligibility, policy coverage, documentation, pre-authorisation, treatment eligibility, financial limits and suspicious billing activity.

The insurer needs a unified platform to monitor this journey from claim submission through adjudication, payment, appeal and recovery.

## Business Problem

Claims, policy, provider, payment, operational and investigation data are fragmented across separate processes and systems.

This makes it difficult for management to:

* Measure claim approval and rejection patterns.
* Identify processing delays and SLA breaches.
* Monitor claim ageing and work-queue backlogs.
* Compare provider performance.
* Reconcile claimed, approved and paid amounts.
* Detect duplicate or suspicious claims.
* Estimate potential financial leakage.
* Prioritise claims for human review.
* Forecast future claim volume and expenditure.

## Main Consulting Question

How can a health insurer reduce claim-processing time and financial leakage while maintaining fair, accurate and consistent claim decisions?

## Project Objective

Build an end-to-end claims intelligence and decision-support platform that integrates, validates, models and analyses health-insurance claims data.

The platform will provide:

* Business KPIs.
* Operational monitoring.
* Financial reconciliation.
* Provider analytics.
* Fraud and anomaly indicators.
* Explainable manual-review risk scores.
* Claim-volume and expenditure forecasts.
* Management recommendations.

## Scope

The project includes:

* Claim and claim-line analysis.
* Member and policy analysis.
* Provider and hospital analysis.
* Adjudication and denial analysis.
* Claims operations and SLA monitoring.
* Financial leakage and recovery analysis.
* Fraud and anomaly detection.
* Manual-review prioritisation.
* Forecasting.
* Excel, SQL, Azure, Snowflake and Power BI implementation.

## Out of Scope

The project will not:

* Process real personally identifiable patient data.
* Automatically reject or approve a claim.
* Provide medical advice.
* Diagnose a medical condition.
* Claim actual financial savings.
* Replace a claims adjuster or medical reviewer.
* Reproduce every table found in a full enterprise claims system.

## Stakeholders

* Executive management.
* Chief Claims Officer.
* Claims operations managers.
* Claims adjusters.
* Medical reviewers.
* Finance and recovery teams.
* Special Investigation Unit.
* Provider network team.
* Policy and product team.
* Customer service and appeals team.
* Compliance and internal audit.
* Data, BI and engineering teams.

## Analytical Modules

1. Executive Claims Intelligence
2. Adjudication and Denial Analysis
3. Claims Operations and SLA Monitoring
4. Financial Leakage and Reconciliation
5. Hospital and Provider Performance
6. Member, Policy and Plan Analysis
7. Fraud and Anomaly Detection
8. Manual-Review Prioritisation
9. Claim Volume and Expenditure Forecasting
10. Management Recommendations

## Data Governance Principle

Every field will be identified as one of the following:

* Source synthetic CMS.
* Source real aggregate CMS.
* Project-generated synthetic.
* Derived.
* Assumed reference.
