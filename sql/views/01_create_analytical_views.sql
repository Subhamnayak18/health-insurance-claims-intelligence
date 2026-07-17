USE HealthInsuranceClaimsDW;
GO

/* =========================================================
   1. CLAIM-LEVEL ANALYTICAL VIEW
   ========================================================= */

CREATE OR ALTER VIEW analytics.vw_ClaimOverview
AS
SELECT
    f.ClaimFactKey,
    f.ClaimKey,
    f.ClaimID,
    f.ClaimType,

    b.BeneID,
    pol.PolicyID,
    pl.PlanID,
    pr.ProviderID,

    cs.ClaimStatus,
    cs.StatusGroup,
    cs.IsOpen,

    dr.DenialReason,

    d_submit.FullDate AS SubmissionDate,
    d_decision.FullDate AS DecisionDate,
    d_payment.FullDate AS PaymentDate,
    d_submit.CalendarYear AS SubmissionYear,
    d_submit.YearMonth AS SubmissionMonth,

    f.PaymentStatus,
    f.PreauthStatus,
    f.ReviewPriority,
    f.QueueName,
    f.AdjusterID,

    f.BilledAmount,
    f.EligibleAmount,
    f.ApprovedAmount,
    f.PaidAmount,
    f.EstimatedLeakageAmount,

    f.TurnaroundDays,
    f.SLATargetDays,
    f.SLABreachFlag,
    f.ManualReviewFlag,
    f.DuplicateIndicator,
    f.HighCostFlag,
    f.FraudAlertFlag,
    f.ProviderRiskScore

FROM fact.[Claim] f

INNER JOIN dim.Beneficiary b
    ON b.BeneficiaryKey = f.BeneficiaryKey

INNER JOIN dim.[Policy] pol
    ON pol.PolicyKey = f.PolicyKey

INNER JOIN dim.[Plan] pl
    ON pl.PlanKey = f.PlanKey

INNER JOIN dim.Provider pr
    ON pr.ProviderKey = f.ProviderKey

INNER JOIN dim.ClaimStatus cs
    ON cs.ClaimStatusKey = f.ClaimStatusKey

LEFT JOIN dim.DenialReason dr
    ON dr.DenialReasonKey = f.DenialReasonKey

INNER JOIN dim.[Date] d_submit
    ON d_submit.DateKey = f.SubmissionDateKey

LEFT JOIN dim.[Date] d_decision
    ON d_decision.DateKey = f.DecisionDateKey

LEFT JOIN dim.[Date] d_payment
    ON d_payment.DateKey = f.PaymentDateKey;
GO


/* =========================================================
   2. MONTHLY CLAIMS VIEW
   ========================================================= */

CREATE OR ALTER VIEW analytics.vw_MonthlyClaims
AS
SELECT
    d.CalendarYear,
    d.MonthNumber,
    d.MonthName,
    d.YearMonth,

    COUNT_BIG(*) AS TotalClaims,

    SUM(f.BilledAmount) AS TotalBilledAmount,
    SUM(f.ApprovedAmount) AS TotalApprovedAmount,
    SUM(f.PaidAmount) AS TotalPaidAmount,

    SUM(
        CASE
            WHEN cs.ClaimStatus = 'REJECTED' THEN 1
            ELSE 0
        END
    ) AS RejectedClaims,

    SUM(
        CASE
            WHEN f.SLABreachFlag = 1 THEN 1
            ELSE 0
        END
    ) AS SLABreachedClaims

FROM fact.[Claim] f

INNER JOIN dim.[Date] d
    ON d.DateKey = f.SubmissionDateKey

INNER JOIN dim.ClaimStatus cs
    ON cs.ClaimStatusKey = f.ClaimStatusKey

GROUP BY
    d.CalendarYear,
    d.MonthNumber,
    d.MonthName,
    d.YearMonth;
GO


/* =========================================================
   3. SLA PERFORMANCE VIEW
   ========================================================= */

CREATE OR ALTER VIEW analytics.vw_SLAPerformance
AS
SELECT
    f.ClaimType,

    COUNT_BIG(*) AS TotalClaims,

    SUM(
        CASE
            WHEN f.SLABreachFlag = 1 THEN 1
            ELSE 0
        END
    ) AS BreachedClaims,

    SUM(
        CASE
            WHEN f.SLABreachFlag = 0 THEN 1
            ELSE 0
        END
    ) AS WithinSLAClaims,

    CAST(
        100.0 *
        SUM(
            CASE
                WHEN f.SLABreachFlag = 1 THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(8,2)
    ) AS SLABreachRate,

    CAST(
        AVG(
            CAST(f.TurnaroundDays AS DECIMAL(18,2))
        )
        AS DECIMAL(18,2)
    ) AS AverageTurnaroundDays

FROM fact.[Claim] f

GROUP BY
    f.ClaimType;
GO


/* =========================================================
   4. PROVIDER PERFORMANCE VIEW
   ========================================================= */

CREATE OR ALTER VIEW analytics.vw_ProviderPerformance
AS
SELECT
    pr.ProviderID,

    COUNT_BIG(*) AS TotalClaims,

    SUM(f.BilledAmount) AS TotalBilledAmount,
    SUM(f.ApprovedAmount) AS TotalApprovedAmount,
    SUM(f.PaidAmount) AS TotalPaidAmount,

    SUM(
        CASE
            WHEN cs.ClaimStatus = 'REJECTED' THEN 1
            ELSE 0
        END
    ) AS RejectedClaims,

    SUM(
        CASE
            WHEN f.SLABreachFlag = 1 THEN 1
            ELSE 0
        END
    ) AS SLABreachedClaims,

    SUM(
        CASE
            WHEN f.FraudAlertFlag = 1 THEN 1
            ELSE 0
        END
    ) AS FraudAlertClaims,

    SUM(f.EstimatedLeakageAmount)
        AS EstimatedLeakageAmount,

    CAST(
        AVG(
            CAST(f.ProviderRiskScore AS DECIMAL(18,4))
        )
        AS DECIMAL(18,4)
    ) AS AverageProviderRiskScore,

    CAST(
        100.0 *
        SUM(
            CASE
                WHEN cs.ClaimStatus = 'REJECTED' THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT_BIG(*), 0)
        AS DECIMAL(8,2)
    ) AS RejectionRate

FROM fact.[Claim] f

INNER JOIN dim.Provider pr
    ON pr.ProviderKey = f.ProviderKey

INNER JOIN dim.ClaimStatus cs
    ON cs.ClaimStatusKey = f.ClaimStatusKey

GROUP BY
    pr.ProviderID;
GO


/* =========================================================
   5. HUMAN-REVIEW QUEUE VIEW
   ========================================================= */

CREATE OR ALTER VIEW analytics.vw_ReviewQueue
AS
SELECT
    f.ClaimKey,
    f.ClaimID,
    f.ClaimType,

    pr.ProviderID,
    cs.ClaimStatus,

    f.ReviewPriority,
    f.QueueName,
    f.AdjusterID,

    f.BilledAmount,
    f.ApprovedAmount,
    f.EstimatedLeakageAmount,

    f.ProviderRiskScore,
    f.FraudAlertFlag,
    f.DuplicateIndicator,
    f.HighCostFlag,
    f.SLABreachFlag,
    f.TurnaroundDays,

    d.FullDate AS SubmissionDate

FROM fact.[Claim] f

INNER JOIN dim.Provider pr
    ON pr.ProviderKey = f.ProviderKey

INNER JOIN dim.ClaimStatus cs
    ON cs.ClaimStatusKey = f.ClaimStatusKey

INNER JOIN dim.[Date] d
    ON d.DateKey = f.SubmissionDateKey

WHERE
    f.ManualReviewFlag = 1
    OR f.FraudAlertFlag = 1
    OR f.DuplicateIndicator = 1;
GO

PRINT 'Analytical views created successfully.';
GO