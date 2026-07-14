# Health Insurance Claims Intelligence & Adjudication Platform

## Project Overview

This project develops an end-to-end health-insurance claims analytics and decision-support platform using official public healthcare data, documented synthetic operational data and derived analytical features.

The platform is designed to help an insurer:

* Analyse claims, approvals and payments.
* Identify claim-processing delays and SLA breaches.
* Compare hospital and provider performance.
* Detect suspicious or anomalous claim activity.
* Estimate potential financial leakage.
* Prioritise claims for manual human review.
* Forecast claim volume and expenditure.
* Recommend operational and financial actions.

## Selected Geography

United States — Medicare-style fee-for-service claims.

The United States was selected because official CMS sources provide well-documented beneficiary, claim, claim-line, diagnosis, procedure and payment structures suitable for data modelling, SQL, Power BI and machine learning.

## Dataset Strategy

### Primary source

CMS Synthetic Medicare Enrollment, Fee-for-Service Claims and Prescription Drug Event Public Use Files.

### External benchmark

CMS Medicare provider utilisation and payment data.

### Project-generated synthetic data

Synthetic operational data will be created for policy rules, claim submissions, pre-authorisations, adjudication decisions, adjustments, work queues, adjusters, appeals, fraud alerts, overpayments and recoveries.

### Derived data

Derived fields will include claim ageing, turnaround time, SLA breaches, financial variances, utilisation metrics, provider risk scores and machine-learning features.

## Technology Stack

* Python
* Excel and Power Query
* SQL Server and Azure SQL Database
* Azure Blob Storage
* Azure Data Factory
* Snowflake
* Power BI and DAX
* Scikit-learn
* XGBoost
* Git and GitHub

## Important Governance Principle

Machine-learning outputs will support manual review and prioritisation. They will not automatically approve or reject insurance claims.

## Project Status

Day 1 — Foundation and dataset strategy.
