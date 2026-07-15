from pathlib import Path
import logging

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = PROJECT_ROOT / "data" / "metadata" / "raw_column_profile.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "metadata" / "cleaning_rule_catalogue.csv"
REPORT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "02_data_understanding"
    / "03_cleaning_plan.md"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


CRITICAL_COLUMNS = {
    "BENE_ID",
    "CLM_ID",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    "CLM_PMT_AMT",
    "LINE_NUM",
    "HCPCS_CD",
    "PRVDR_NUM",
    "ORG_NPI_NUM",
}


def classify_business_role(column_name: str) -> str:
    name = column_name.upper()

    if name.endswith("_ID") or name in {"BENE_ID", "CLM_ID", "LINE_NUM"}:
        return "identifier"

    if any(term in name for term in ["AMT", "PMT", "CHRG", "PAY"]):
        return "financial"

    if any(term in name for term in ["DATE", "_DT", "YEAR", "MONTH"]):
        return "date"

    if any(term in name for term in ["DGNS", "DIAG", "ICD"]):
        return "diagnosis"

    if any(term in name for term in ["HCPCS", "PRCDR", "PROCEDURE"]):
        return "procedure"

    if any(term in name for term in ["PRVDR", "NPI", "PHYSN"]):
        return "provider"

    if any(term in name for term in ["STATE", "ZIP", "CNTY", "GEO"]):
        return "geography"

    if any(term in name for term in ["IND", "SW", "FLAG"]):
        return "indicator"

    return "other"


def recommend_action(row: pd.Series) -> tuple[str, str, str]:
    column_name = row["column_name"]
    missing_percentage = row["missing_percentage"]
    unique_count = row["unique_count"]

    if column_name in CRITICAL_COLUMNS or column_name.endswith("_ID"):
        return (
            "KEEP_CRITICAL",
            "High",
            "Required for relationships, claim grain or core KPI calculations.",
        )

    if unique_count <= 1:
        return (
            "REVIEW_CONSTANT",
            "Medium",
            "Column contains one or no distinct values in the profiling sample.",
        )

    if missing_percentage >= 95:
        return (
            "REVIEW_HIGH_MISSING",
            "Medium",
            "At least 95% of sample values are missing.",
        )

    if missing_percentage >= 70:
        return (
            "REVIEW_SPARSE",
            "Low",
            "Column is sparse but may apply only to specific claim types.",
        )

    return (
        "KEEP_INITIAL",
        "Low",
        "Column has acceptable initial completeness and variation.",
    )


def create_report(dataframe: pd.DataFrame) -> None:
    action_counts = (
        dataframe.groupby(
            ["dataset_name", "recommended_action"],
            dropna=False,
        )
        .size()
        .reset_index(name="column_count")
    )

    lines = [
        "# Cleaning Plan",
        "",
        "## Purpose",
        "",
        "This document records the initial column-level cleaning decisions "
        "for the selected CMS synthetic claims datasets.",
        "",
        "No columns have been removed at this stage.",
        "",
        "## Decision Rules",
        "",
        "- Critical identifiers and financial fields are retained.",
        "- Constant columns are reviewed before removal.",
        "- Columns with at least 95% missing values require detailed review.",
        "- Sparse columns are not automatically deleted because they may apply "
        "only to particular claim types.",
        "- Final cleaning decisions will be based on business relevance, "
        "data grain and source documentation.",
        "",
        "## Summary",
        "",
    ]

    for row in action_counts.itertuples(index=False):
        lines.append(
            f"- {row.dataset_name} — {row.recommended_action}: "
            f"{row.column_count} columns"
        )

    lines.extend(
        [
            "",
            "## Governance Rule",
            "",
            "No raw source file will be modified. Cleaned outputs will be written "
            "to separate processed-data folders.",
        ]
    )

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Column profile was not found: {PROFILE_PATH}"
        )

    profile = pd.read_csv(PROFILE_PATH)

    profile["missing_percentage"] = pd.to_numeric(
        profile["missing_percentage"],
        errors="coerce",
    ).fillna(0)

    profile["unique_count"] = pd.to_numeric(
        profile["unique_count"],
        errors="coerce",
    ).fillna(0)

    profile["business_role"] = profile["column_name"].apply(
        classify_business_role
    )

    recommendations = profile.apply(
        recommend_action,
        axis=1,
        result_type="expand",
    )

    recommendations.columns = [
        "recommended_action",
        "priority",
        "decision_reason",
    ]

    cleaning_plan = pd.concat(
        [profile, recommendations],
        axis=1,
    )

    cleaning_plan = cleaning_plan[
        [
            "dataset_name",
            "column_name",
            "business_role",
            "missing_percentage",
            "unique_count",
            "recommended_action",
            "priority",
            "decision_reason",
            "example_values",
        ]
    ]

    cleaning_plan.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    create_report(cleaning_plan)

    logger.info("Cleaning catalogue saved to %s", OUTPUT_PATH)
    logger.info("Cleaning plan saved to %s", REPORT_PATH)
    logger.info("Column triage completed successfully")


if __name__ == "__main__":
    main()