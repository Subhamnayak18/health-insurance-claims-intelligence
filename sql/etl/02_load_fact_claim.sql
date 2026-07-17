USE HealthInsuranceClaimsDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    TRUNCATE TABLE fact.[Claim];

    INSERT INTO fact.[Claim] (
        ClaimKey,
        ClaimID,
        ClaimType,

        BeneficiaryKey,
        PolicyKey,
        PlanKey,
        ProviderKey,
        ClaimStatusKey,
        DenialReasonKey,

        ClaimFromDateKey,
        ClaimThruDateKey,
        SubmissionDateKey,
        DecisionDateKey,
        PaymentDateKey,
        AnalysisDateKey,

        PaymentStatus,
        PreauthStatus,
        ReviewPriority,
        QueueName,
        AdjusterID,
        DataProvenance,

        DocumentsCompleteFlag,
        PolicyActiveFlag,
        TreatmentCoveredFlag,
        WaitingPeriodFlag,
        PreauthRequiredFlag,
        SLABreachFlag,
        ManualReviewFlag,
        DuplicateIndicator,
        HighCostFlag,
        FraudAlertFlag,

        BilledAmount,
        EligibleAmount,
        DeductibleAmount,
        CopayAmount,
        NonPayableAmount,
        AdjustmentAmount,
        ApprovedAmount,
        PaidAmount,
        SourceCMSPaymentAmount,
        EstimatedLeakageAmount,

        TurnaroundDays,
        SLATargetDays,
        ProviderRiskScore
    )
    SELECT
        s.CLAIM_KEY,
        s.CLAIM_ID,
        s.CLAIM_TYPE,

        b.BeneficiaryKey,
        pol.PolicyKey,
        pl.PlanKey,
        pr.ProviderKey,
        cs.ClaimStatusKey,
        dr.DenialReasonKey,

        d_from.DateKey,
        d_thru.DateKey,
        d_submit.DateKey,
        d_decision.DateKey,
        d_payment.DateKey,
        d_analysis.DateKey,

        s.PAYMENT_STATUS,
        s.PREAUTH_STATUS,
        s.REVIEW_PRIORITY,
        s.QUEUE_NAME,
        s.ADJUSTER_ID,
        s.DATA_PROVENANCE,

        s.DOCUMENTS_COMPLETE_FLAG,
        s.POLICY_ACTIVE_FLAG,
        s.TREATMENT_COVERED_FLAG,
        s.WAITING_PERIOD_FLAG,
        s.PREAUTH_REQUIRED_FLAG,
        s.SLA_BREACH_FLAG,
        s.MANUAL_REVIEW_FLAG,
        s.DUPLICATE_INDICATOR,
        s.HIGH_COST_FLAG,
        s.FRAUD_ALERT_FLAG,

        s.BILLED_AMOUNT,
        s.ELIGIBLE_AMOUNT,
        s.DEDUCTIBLE_AMOUNT,
        s.COPAY_AMOUNT,
        s.NON_PAYABLE_AMOUNT,
        s.ADJUSTMENT_AMOUNT,
        s.APPROVED_AMOUNT,
        s.PAID_AMOUNT,
        s.SOURCE_CMS_PAYMENT_AMOUNT,
        s.ESTIMATED_LEAKAGE_AMOUNT,

        s.TURNAROUND_DAYS,
        s.SLA_TARGET_DAYS,
        s.PROVIDER_RISK_SCORE

    FROM stg.ClaimOperations s

    INNER JOIN dim.Beneficiary b
        ON b.BeneID = s.BENE_ID

    INNER JOIN dim.[Policy] pol
        ON pol.PolicyID = s.POLICY_ID

    INNER JOIN dim.[Plan] pl
        ON pl.PlanID = s.PLAN_ID

    INNER JOIN dim.Provider pr
        ON pr.ProviderID = s.PRIMARY_PROVIDER_ID

    INNER JOIN dim.ClaimStatus cs
        ON cs.ClaimStatus = s.CLAIM_STATUS

    LEFT JOIN dim.DenialReason dr
        ON dr.DenialReason = s.DENIAL_REASON

    INNER JOIN dim.[Date] d_from
        ON d_from.FullDate = s.CLAIM_FROM_DATE

    INNER JOIN dim.[Date] d_thru
        ON d_thru.FullDate = s.CLAIM_THRU_DATE

    INNER JOIN dim.[Date] d_submit
        ON d_submit.FullDate = s.SUBMISSION_DATE

    LEFT JOIN dim.[Date] d_decision
        ON d_decision.FullDate = s.DECISION_DATE

    LEFT JOIN dim.[Date] d_payment
        ON d_payment.FullDate = s.PAYMENT_DATE

    INNER JOIN dim.[Date] d_analysis
        ON d_analysis.FullDate = s.ANALYSIS_DATE;

    COMMIT TRANSACTION;

    PRINT 'Fact claim loading completed successfully.';

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO