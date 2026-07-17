USE HealthInsuranceClaimsDW;
GO

/* 1. Executive claims KPIs */
SELECT
    COUNT(*) AS TotalClaims,

    SUM(CASE
        WHEN ClaimStatus IN ('APPROVED', 'PARTIALLY_APPROVED')
        THEN 1 ELSE 0
    END) AS ApprovedClaims,

    CAST(
        100.0 * SUM(CASE
            WHEN ClaimStatus IN ('APPROVED', 'PARTIALLY_APPROVED')
            THEN 1 ELSE 0
        END) / COUNT(*)
        AS DECIMAL(8,2)
    ) AS ApprovalRate,

    CAST(
        100.0 * SUM(CASE
            WHEN ClaimStatus = 'REJECTED'
            THEN 1 ELSE 0
        END) / COUNT(*)
        AS DECIMAL(8,2)
    ) AS RejectionRate,

    SUM(BilledAmount) AS TotalBilledAmount,
    SUM(ApprovedAmount) AS TotalApprovedAmount,
    SUM(PaidAmount) AS TotalPaidAmount,

    CAST(
        100.0 * SUM(PaidAmount)
        / NULLIF(SUM(ApprovedAmount), 0)
        AS DECIMAL(8,2)
    ) AS SettlementRate

FROM analytics.vw_ClaimOverview;
GO


/* 2. Claim-status performance */
SELECT
    ClaimStatus,
    COUNT(*) AS TotalClaims,
    SUM(BilledAmount) AS BilledAmount,
    SUM(ApprovedAmount) AS ApprovedAmount,
    SUM(PaidAmount) AS PaidAmount
FROM analytics.vw_ClaimOverview
GROUP BY ClaimStatus
ORDER BY TotalClaims DESC;
GO


/* 3. SLA performance */
SELECT *
FROM analytics.vw_SLAPerformance
ORDER BY SLABreachRate DESC;
GO


/* 4. Monthly claims trend */
SELECT
    YearMonth,
    TotalClaims,
    TotalBilledAmount,
    TotalApprovedAmount,
    TotalPaidAmount,
    RejectedClaims,
    SLABreachedClaims
FROM analytics.vw_MonthlyClaims
ORDER BY YearMonth;
GO


/* 5. Highest-risk providers */
SELECT TOP 20
    ProviderID,
    TotalClaims,
    RejectedClaims,
    RejectionRate,
    FraudAlertClaims,
    EstimatedLeakageAmount,
    AverageProviderRiskScore
FROM analytics.vw_ProviderPerformance
WHERE TotalClaims >= 10
ORDER BY
    EstimatedLeakageAmount DESC,
    AverageProviderRiskScore DESC;
GO


/* 6. Highest-priority human-review claims */
SELECT TOP 50
    ClaimKey,
    ClaimType,
    ProviderID,
    ClaimStatus,
    ReviewPriority,
    QueueName,
    BilledAmount,
    EstimatedLeakageAmount,
    ProviderRiskScore,
    FraudAlertFlag,
    DuplicateIndicator,
    SLABreachFlag
FROM analytics.vw_ReviewQueue
ORDER BY
    CASE ReviewPriority
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        ELSE 4
    END,
    EstimatedLeakageAmount DESC;
GO