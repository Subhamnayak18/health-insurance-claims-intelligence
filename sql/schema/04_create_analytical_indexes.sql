USE HealthInsuranceClaimsDW;
GO

/* Monthly claims analysis */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_FactClaim_SubmissionDate'
      AND object_id = OBJECT_ID('fact.[Claim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_SubmissionDate
    ON fact.[Claim] (SubmissionDateKey)
    INCLUDE (
        ClaimStatusKey,
        ClaimType,
        BilledAmount,
        ApprovedAmount,
        PaidAmount
    );
END;
GO


/* Claim-status and SLA analysis */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_FactClaim_Status_SLA'
      AND object_id = OBJECT_ID('fact.[Claim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_Status_SLA
    ON fact.[Claim] (
        ClaimStatusKey,
        SLABreachFlag
    )
    INCLUDE (
        ClaimType,
        TurnaroundDays,
        BilledAmount,
        ApprovedAmount,
        PaidAmount
    );
END;
GO


/* Provider performance */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_FactClaim_Provider'
      AND object_id = OBJECT_ID('fact.[Claim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_Provider
    ON fact.[Claim] (ProviderKey)
    INCLUDE (
        ClaimStatusKey,
        BilledAmount,
        ApprovedAmount,
        PaidAmount,
        ProviderRiskScore,
        EstimatedLeakageAmount,
        FraudAlertFlag
    );
END;
GO


/* Plan and claim-type analysis */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_FactClaim_Plan_ClaimType'
      AND object_id = OBJECT_ID('fact.[Claim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_Plan_ClaimType
    ON fact.[Claim] (
        PlanKey,
        ClaimType
    )
    INCLUDE (
        ClaimStatusKey,
        BilledAmount,
        ApprovedAmount,
        PaidAmount
    );
END;
GO


/* Human-review and fraud queue */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_FactClaim_ReviewQueue'
      AND object_id = OBJECT_ID('fact.[Claim]')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactClaim_ReviewQueue
    ON fact.[Claim] (
        ManualReviewFlag,
        FraudAlertFlag,
        ReviewPriority
    )
    INCLUDE (
        ProviderKey,
        ClaimStatusKey,
        QueueName,
        ProviderRiskScore,
        EstimatedLeakageAmount
    );
END;
GO

PRINT 'Analytical indexes created successfully.';
GO