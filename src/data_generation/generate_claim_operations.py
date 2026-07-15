from pathlib import Path
import logging

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "analytical"
    / "claim_header.parquet"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "synthetic"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"
DOCS_DIR = PROJECT_ROOT / "docs" / "02_data_understanding"

OUTPUT_PATH = OUTPUT_DIR / "claim_operations.parquet"
AUDIT_PATH = METADATA_DIR / "synthetic_claim_operations_audit.csv"
REPORT_PATH = DOCS_DIR / "07_synthetic_claim_operations.md"

RANDOM_SEED = 42

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def numeric_column(
    dataframe: pd.DataFrame,
    column_name: str,
) -> pd.Series:
    if column_name not in dataframe.columns:
        return pd.Series(
            np.nan,
            index=dataframe.index,
            dtype="float64",
        )

    return pd.to_numeric(
        dataframe[column_name],
        errors="coerce",
    )


def build_billed_amount(
    claims: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.Series:
    claim_charge = numeric_column(
        claims,
        "CLAIM_TOTAL_CHARGE_AMOUNT",
    )

    line_charge = numeric_column(
        claims,
        "LINE_SUBMITTED_CHARGE_AMOUNT",
    )

    source_payment = numeric_column(
        claims,
        "CLAIM_PAYMENT_AMOUNT",
    )

    billed_amount = claim_charge.where(claim_charge > 0)

    billed_amount = billed_amount.combine_first(
        line_charge.where(line_charge > 0)
    )

    payment_fallback = source_payment.where(
        source_payment > 0
    ) * rng.uniform(1.10, 1.50, len(claims))

    billed_amount = billed_amount.combine_first(
        payment_fallback
    )

    default_amounts = claims["CLAIM_TYPE"].map(
        {
            "CARRIER": 300.0,
            "OUTPATIENT": 2_000.0,
            "INPATIENT": 18_000.0,
        }
    )

    default_amounts = (
        default_amounts
        * rng.uniform(0.80, 1.20, len(claims))
    )

    return (
        billed_amount
        .combine_first(default_amounts)
        .fillna(1_000.0)
        .clip(lower=1)
        .round(2)
    )


def create_audit(dataframe: pd.DataFrame) -> pd.DataFrame:
    final_statuses = {
        "APPROVED",
        "PARTIALLY_APPROVED",
        "REJECTED",
    }

    open_statuses = {
        "PENDING",
        "MANUAL_REVIEW",
    }

    hierarchy_violations = (
        (dataframe["BILLED_AMOUNT"] < dataframe["ELIGIBLE_AMOUNT"])
        | (
            dataframe["ELIGIBLE_AMOUNT"]
            < dataframe["APPROVED_AMOUNT"]
        )
        | (
            dataframe["APPROVED_AMOUNT"]
            < dataframe["PAID_AMOUNT"]
        )
    ).sum()

    negative_amount_rows = (
        dataframe[
            [
                "BILLED_AMOUNT",
                "ELIGIBLE_AMOUNT",
                "APPROVED_AMOUNT",
                "PAID_AMOUNT",
            ]
        ]
        .lt(0)
        .any(axis=1)
        .sum()
    )

    rejected_positive_amount = (
        dataframe["CLAIM_STATUS"].eq("REJECTED")
        & (
            dataframe["APPROVED_AMOUNT"].gt(0)
            | dataframe["PAID_AMOUNT"].gt(0)
        )
    ).sum()

    open_with_decision = (
        dataframe["CLAIM_STATUS"].isin(open_statuses)
        & dataframe["DECISION_DATE"].notna()
    ).sum()

    final_without_decision = (
        dataframe["CLAIM_STATUS"].isin(final_statuses)
        & dataframe["DECISION_DATE"].isna()
    ).sum()

    checks = [
        {
            "metric": "total_claims",
            "value": len(dataframe),
            "expected_rule": "Greater than zero",
            "status": "PASS" if len(dataframe) > 0 else "FAIL",
        },
        {
            "metric": "unique_claim_keys",
            "value": dataframe["CLAIM_KEY"].nunique(),
            "expected_rule": "Equal to total claims",
            "status": (
                "PASS"
                if dataframe["CLAIM_KEY"].nunique()
                == len(dataframe)
                else "FAIL"
            ),
        },
        {
            "metric": "duplicate_claim_keys",
            "value": int(
                dataframe["CLAIM_KEY"].duplicated().sum()
            ),
            "expected_rule": "0",
            "status": (
                "PASS"
                if not dataframe["CLAIM_KEY"].duplicated().any()
                else "FAIL"
            ),
        },
        {
            "metric": "financial_hierarchy_violations",
            "value": int(hierarchy_violations),
            "expected_rule": "0",
            "status": (
                "PASS"
                if hierarchy_violations == 0
                else "FAIL"
            ),
        },
        {
            "metric": "negative_amount_rows",
            "value": int(negative_amount_rows),
            "expected_rule": "0",
            "status": (
                "PASS"
                if negative_amount_rows == 0
                else "FAIL"
            ),
        },
        {
            "metric": "rejected_claims_with_positive_payment",
            "value": int(rejected_positive_amount),
            "expected_rule": "0",
            "status": (
                "PASS"
                if rejected_positive_amount == 0
                else "FAIL"
            ),
        },
        {
            "metric": "open_claims_with_decision_date",
            "value": int(open_with_decision),
            "expected_rule": "0",
            "status": (
                "PASS"
                if open_with_decision == 0
                else "FAIL"
            ),
        },
        {
            "metric": "final_claims_without_decision_date",
            "value": int(final_without_decision),
            "expected_rule": "0",
            "status": (
                "PASS"
                if final_without_decision == 0
                else "FAIL"
            ),
        },
    ]

    for status, count in (
        dataframe["CLAIM_STATUS"]
        .value_counts()
        .sort_index()
        .items()
    ):
        checks.append(
            {
                "metric": f"status_count_{status.lower()}",
                "value": int(count),
                "expected_rule": "Informational",
                "status": "INFO",
            }
        )

    return pd.DataFrame(checks)


def write_report(dataframe: pd.DataFrame) -> None:
    status_counts = (
        dataframe["CLAIM_STATUS"]
        .value_counts()
        .sort_index()
    )

    lines = [
        "# Synthetic Claim Operations",
        "",
        "## Purpose",
        "",
        "CMS provides claim and payment structures but does not contain "
        "the complete internal adjudication workflow.",
        "",
        "This dataset adds documented project-generated operational fields.",
        "",
        "## Final Grain",
        "",
        "One row per `CLAIM_KEY`.",
        "",
        "## Generated Information",
        "",
        "- Policy and plan assignment",
        "- Claim submission and decision dates",
        "- Documentation and pre-authorisation status",
        "- Claim status and denial reason",
        "- Financial adjustments",
        "- SLA and turnaround-time indicators",
        "- Manual-review and fraud indicators",
        "- Work queue, priority and adjuster assignment",
        "",
        "## Status Distribution",
        "",
    ]

    for status, count in status_counts.items():
        lines.append(f"- {status}: {count:,}")

    lines.extend(
        [
            "",
            "## Financial Control",
            "",
            "`BILLED_AMOUNT >= ELIGIBLE_AMOUNT >= "
            "APPROVED_AMOUNT >= PAID_AMOUNT`",
            "",
            "## Governance",
            "",
            "All workflow and adjudication fields are classified as "
            "`PROJECT_SYNTHETIC`.",
            "",
            "Synthetic claim decisions are created for portfolio analysis "
            "and do not represent real insurance decisions.",
        ]
    )

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Claim-header file was not found: {INPUT_PATH}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(RANDOM_SEED)

    claims = pd.read_parquet(INPUT_PATH)
    claim_count = len(claims)

    if claims["CLAIM_KEY"].duplicated().any():
        raise ValueError(
            "Duplicate claim keys were found in the claim header."
        )

    claim_type = claims["CLAIM_TYPE"].astype("string")
    beneficiary_id = claims["BENE_ID"].astype("string")

    claim_from_date = pd.to_datetime(
        claims["CLAIM_FROM_DATE"],
        errors="coerce",
    )

    claim_thru_date = pd.to_datetime(
        claims["CLAIM_THRU_DATE"],
        errors="coerce",
    )

    provider_id = (
        claims["PRIMARY_PROVIDER_ID"]
        .astype("string")
        .fillna("UNKNOWN_PROVIDER")
    )

    beneficiary_hash = pd.util.hash_pandas_object(
        beneficiary_id.fillna("UNKNOWN_MEMBER"),
        index=False,
    ).to_numpy()

    provider_hash = pd.util.hash_pandas_object(
        provider_id,
        index=False,
    ).to_numpy()

    plan_labels = np.array(
        [
            "PLAN_BASIC",
            "PLAN_STANDARD",
            "PLAN_PREMIUM",
        ],
        dtype=object,
    )

    plan_id = plan_labels[beneficiary_hash % 3]

    deductible_rates = pd.Series(plan_id).map(
        {
            "PLAN_BASIC": 0.08,
            "PLAN_STANDARD": 0.04,
            "PLAN_PREMIUM": 0.01,
        }
    ).to_numpy()

    copay_rates = pd.Series(plan_id).map(
        {
            "PLAN_BASIC": 0.15,
            "PLAN_STANDARD": 0.10,
            "PLAN_PREMIUM": 0.05,
        }
    ).to_numpy()

    billed_amount = build_billed_amount(
        claims=claims,
        rng=rng,
    )

    policy_active = rng.random(claim_count) >= 0.015
    treatment_covered = rng.random(claim_count) >= 0.04
    documents_complete = rng.random(claim_count) >= 0.06
    waiting_period_flag = rng.random(claim_count) < 0.01

    preauth_probability = claim_type.map(
        {
            "INPATIENT": 0.70,
            "OUTPATIENT": 0.20,
            "CARRIER": 0.08,
        }
    ).fillna(0.10).to_numpy()

    preauth_required = (
        rng.random(claim_count)
        < preauth_probability
    )

    preauth_status = np.full(
        claim_count,
        "NOT_REQUIRED",
        dtype=object,
    )

    preauth_roll = rng.random(claim_count)

    preauth_status[
        preauth_required & (preauth_roll < 0.86)
    ] = "APPROVED"

    preauth_status[
        preauth_required
        & (preauth_roll >= 0.86)
        & (preauth_roll < 0.94)
    ] = "MISSING"

    preauth_status[
        preauth_required & (preauth_roll >= 0.94)
    ] = "DENIED"

    duplicate_indicator = (
        rng.random(claim_count) < 0.004
    )

    provider_risk_score = (
        provider_hash % 1_000
    ) / 1_000

    provider_risk_flag = provider_risk_score >= 0.97

    high_cost_threshold = billed_amount.groupby(
        claim_type
    ).transform(
        lambda values: values.quantile(0.97)
    )

    high_cost_flag = (
        billed_amount >= high_cost_threshold
    )

    rejection_rule = (
        ~policy_active
        | ~treatment_covered
        | waiting_period_flag
        | (preauth_status == "DENIED")
    )

    random_pending = rng.random(claim_count) < 0.025

    pending_rule = (
        ~rejection_rule
        & (
            ~documents_complete
            | (
                (preauth_status == "MISSING")
                & (rng.random(claim_count) < 0.70)
            )
            | random_pending
        )
    )

    manual_review_rule = (
        ~rejection_rule
        & ~pending_rule
        & (
            duplicate_indicator
            | provider_risk_flag
            | high_cost_flag
            | (preauth_status == "MISSING")
        )
    )

    partial_rule = (
        ~rejection_rule
        & ~pending_rule
        & ~manual_review_rule
        & (rng.random(claim_count) < 0.15)
    )

    claim_status = np.full(
        claim_count,
        "APPROVED",
        dtype=object,
    )

    claim_status[partial_rule] = "PARTIALLY_APPROVED"
    claim_status[manual_review_rule] = "MANUAL_REVIEW"
    claim_status[pending_rule] = "PENDING"
    claim_status[rejection_rule] = "REJECTED"

    denial_reason = np.select(
        [
            ~policy_active,
            ~treatment_covered,
            waiting_period_flag,
            preauth_status == "DENIED",
        ],
        [
            "POLICY_INACTIVE",
            "TREATMENT_NOT_COVERED",
            "WAITING_PERIOD",
            "PREAUTH_DENIED",
        ],
        default="OTHER",
    )

    denial_reason = pd.Series(
        denial_reason,
        dtype="string",
    ).where(claim_status == "REJECTED")

    eligibility_ratio = rng.uniform(
        0.70,
        0.96,
        claim_count,
    )

    eligible_amount = billed_amount * eligibility_ratio

    ineligible_policy = (
        ~policy_active
        | ~treatment_covered
        | waiting_period_flag
    )

    eligible_amount = eligible_amount.mask(
        ineligible_policy,
        0,
    ).round(2)

    deductible_amount = (
        eligible_amount * deductible_rates
    ).round(2)

    copay_base = (
        eligible_amount - deductible_amount
    ).clip(lower=0)

    copay_amount = (
        copay_base * copay_rates
    ).round(2)

    amount_before_adjustment = (
        eligible_amount
        - deductible_amount
        - copay_amount
    ).clip(lower=0)

    adjustment_amount = pd.Series(
        np.zeros(claim_count),
        index=claims.index,
        dtype="float64",
    )

    approved_mask = claim_status == "APPROVED"
    partial_mask = claim_status == "PARTIALLY_APPROVED"
    rejected_mask = claim_status == "REJECTED"

    adjustment_amount.loc[approved_mask] = (
        amount_before_adjustment.loc[approved_mask]
        * rng.uniform(
            0,
            0.02,
            approved_mask.sum(),
        )
    )

    adjustment_amount.loc[partial_mask] = (
        amount_before_adjustment.loc[partial_mask]
        * rng.uniform(
            0.10,
            0.35,
            partial_mask.sum(),
        )
    )

    adjustment_amount.loc[rejected_mask] = (
        amount_before_adjustment.loc[rejected_mask]
    )

    adjustment_amount = adjustment_amount.round(2)

    approved_amount = (
        amount_before_adjustment
        - adjustment_amount
    ).clip(lower=0)

    open_mask = np.isin(
        claim_status,
        ["PENDING", "MANUAL_REVIEW"],
    )

    approved_amount.loc[open_mask] = 0
    approved_amount = approved_amount.round(2)

    payable_mask = np.isin(
        claim_status,
        ["APPROVED", "PARTIALLY_APPROVED"],
    )

    payment_completed = (
        payable_mask
        & (rng.random(claim_count) < 0.90)
    )

    paid_amount = pd.Series(
        np.zeros(claim_count),
        index=claims.index,
        dtype="float64",
    )

    paid_amount.loc[payment_completed] = (
        approved_amount.loc[payment_completed]
        * rng.uniform(
            0.98,
            1.00,
            payment_completed.sum(),
        )
    )

    paid_amount = np.minimum(
        paid_amount.round(2),
        approved_amount,
    )

    payment_status = np.full(
        claim_count,
        "NOT_READY",
        dtype=object,
    )

    payment_status[rejected_mask] = "NOT_PAYABLE"

    payment_status[
        payable_mask & ~payment_completed
    ] = "PAYMENT_PENDING"

    payment_status[payment_completed] = "PAID"

    non_payable_amount = (
        billed_amount - eligible_amount
    ).clip(lower=0).round(2)

    submission_delay = rng.integers(
        0,
        8,
        claim_count,
    )

    submission_date = (
        claim_thru_date.fillna(claim_from_date)
        + pd.to_timedelta(submission_delay, unit="D")
    )

    decision_delay = rng.integers(
        1,
        15,
        claim_count,
    )

    decision_date = (
        submission_date
        + pd.to_timedelta(decision_delay, unit="D")
    )

    decision_date = decision_date.mask(open_mask)

    payment_delay = rng.integers(
        1,
        8,
        claim_count,
    )

    payment_date = (
        decision_date
        + pd.to_timedelta(payment_delay, unit="D")
    ).where(payment_completed)

    analysis_date = (
        submission_date.max()
        + pd.Timedelta(days=45)
    )

    turnaround_days = (
        decision_date.fillna(analysis_date)
        - submission_date
    ).dt.days.clip(lower=0)

    sla_target_days = claim_type.map(
        {
            "CARRIER": 7,
            "OUTPATIENT": 10,
            "INPATIENT": 15,
        }
    ).fillna(10).astype("Int64")

    sla_breach_flag = (
        turnaround_days > sla_target_days
    )

    manual_review_flag = (
        claim_status == "MANUAL_REVIEW"
    )

    fraud_alert_flag = (
        duplicate_indicator
        | provider_risk_flag
    )

    leakage_factor = rng.uniform(
        0.01,
        0.08,
        claim_count,
    )

    estimated_leakage_amount = np.where(
        fraud_alert_flag | high_cost_flag,
        billed_amount * leakage_factor,
        0,
    )

    review_priority = np.full(
        claim_count,
        "LOW",
        dtype=object,
    )

    review_priority[
        np.isin(
            claim_status,
            ["PENDING", "PARTIALLY_APPROVED"],
        )
    ] = "MEDIUM"

    review_priority[manual_review_flag] = "HIGH"

    review_priority[
        fraud_alert_flag & high_cost_flag
    ] = "CRITICAL"

    queue_name = np.full(
        claim_count,
        "CLOSED",
        dtype=object,
    )

    queue_name[claim_status == "PENDING"] = (
        "DOCUMENTATION_QUEUE"
    )

    queue_name[manual_review_flag] = (
        "MANUAL_REVIEW_QUEUE"
    )

    queue_name[fraud_alert_flag] = "SIU_QUEUE"

    adjuster_number = rng.integers(
        1,
        31,
        claim_count,
    )

    operations = pd.DataFrame(
        {
            "CLAIM_KEY": claims["CLAIM_KEY"],
            "CLAIM_ID": claims["CLAIM_ID"],
            "CLAIM_TYPE": claim_type,
            "BENE_ID": beneficiary_id,
            "POLICY_ID": (
                "POL-" + beneficiary_id.fillna("UNKNOWN")
            ),
            "PLAN_ID": plan_id,
            "PRIMARY_PROVIDER_ID": provider_id,
            "CLAIM_FROM_DATE": claim_from_date,
            "CLAIM_THRU_DATE": claim_thru_date,
            "SUBMISSION_DATE": submission_date,
            "DECISION_DATE": decision_date,
            "PAYMENT_DATE": payment_date,
            "CLAIM_STATUS": claim_status,
            "DENIAL_REASON": denial_reason,
            "PAYMENT_STATUS": payment_status,
            "DOCUMENTS_COMPLETE_FLAG": documents_complete,
            "POLICY_ACTIVE_FLAG": policy_active,
            "TREATMENT_COVERED_FLAG": treatment_covered,
            "WAITING_PERIOD_FLAG": waiting_period_flag,
            "PREAUTH_REQUIRED_FLAG": preauth_required,
            "PREAUTH_STATUS": preauth_status,
            "BILLED_AMOUNT": billed_amount,
            "ELIGIBLE_AMOUNT": eligible_amount,
            "DEDUCTIBLE_AMOUNT": deductible_amount,
            "COPAY_AMOUNT": copay_amount,
            "NON_PAYABLE_AMOUNT": non_payable_amount,
            "ADJUSTMENT_AMOUNT": adjustment_amount,
            "APPROVED_AMOUNT": approved_amount,
            "PAID_AMOUNT": paid_amount,
            "SOURCE_CMS_PAYMENT_AMOUNT": numeric_column(
                claims,
                "CLAIM_PAYMENT_AMOUNT",
            ),
            "TURNAROUND_DAYS": turnaround_days,
            "SLA_TARGET_DAYS": sla_target_days,
            "SLA_BREACH_FLAG": sla_breach_flag,
            "MANUAL_REVIEW_FLAG": manual_review_flag,
            "DUPLICATE_INDICATOR": duplicate_indicator,
            "HIGH_COST_FLAG": high_cost_flag,
            "PROVIDER_RISK_SCORE": provider_risk_score.round(3),
            "FRAUD_ALERT_FLAG": fraud_alert_flag,
            "ESTIMATED_LEAKAGE_AMOUNT": (
                np.round(estimated_leakage_amount, 2)
            ),
            "REVIEW_PRIORITY": review_priority,
            "QUEUE_NAME": queue_name,
            "ADJUSTER_ID": (
                pd.Series(adjuster_number)
                .map(lambda value: f"ADJ-{value:03d}")
            ),
            "ANALYSIS_DATE": analysis_date,
            "DATA_PROVENANCE": "PROJECT_SYNTHETIC",
        }
    )

    operations.to_parquet(
        OUTPUT_PATH,
        index=False,
        compression="snappy",
    )

    audit = create_audit(operations)

    audit.to_csv(
        AUDIT_PATH,
        index=False,
    )

    write_report(operations)

    logger.info(
        "Synthetic operations created for %s claims",
        f"{len(operations):,}",
    )

    logger.info("Output saved to %s", OUTPUT_PATH)
    logger.info("Audit saved to %s", AUDIT_PATH)


if __name__ == "__main__":
    main()