# Data Provenance Categories

## SOURCE_SYNTHETIC_CMS

Data received directly from an official CMS synthetic public-use dataset.

## SOURCE_REAL_AGGREGATE_CMS

Aggregated real-world information released publicly by CMS.

## PROJECT_SYNTHETIC

Data generated specifically for this portfolio project.

## DERIVED

Data calculated using source or project-synthetic fields.

## DERIVED_FROM_SOURCE_SYNTHETIC_CMS

The new Gold claim fact uses this label for fields derived from CMS synthetic source records only. Simulated adjudication fields are kept in the original operational model. No real CMS provider aggregate files are currently present; `SOURCE_REAL_AGGREGATE_CMS` is a reserved category, not an implemented integration.

## ASSUMED_REFERENCE

A documented business assumption, threshold or reference rule.

## Governance Rule

No project-generated or CMS synthetic patient record may be described as a real individual patient record.
