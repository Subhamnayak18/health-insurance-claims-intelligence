USE HealthInsuranceClaimsDW;
GO

/* Claims summary with optional filters */
CREATE OR ALTER PROCEDURE analytics.usp_ClaimsSummary
    @StartDate DATE = NULL,
    @EndDate DATE = NULL,
    @ClaimType VARCHAR(20) = NULL,
    @ClaimStatus VARCHAR(30) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        COUNT(*) AS TotalClaims,
        SUM(BilledAmount) AS TotalBilledAmount,
        SUM(ApprovedAmount) AS TotalApprovedAmount,
        SUM(PaidAmount) AS TotalPaidAmount,

        CAST(
            100.0 * SUM(
                CASE
                    WHEN ClaimStatus IN (
                        'APPROVED',
                        'PARTIALLY_APPROVED'
                    )
                    THEN 1 ELSE 0
                END
            ) / NULLIF(COUNT(*), 0)
            AS DECIMAL(8,2)
        ) AS ApprovalRate,

        CAST(
            100.0 * SUM(
                CASE WHEN SLABreachFlag = 1
                THEN 1 ELSE 0 END
            ) / NULLIF(COUNT(*), 0)
            AS DECIMAL(8,2)
        ) AS SLABreachRate

    FROM analytics.vw_ClaimOverview
    WHERE
        (@StartDate IS NULL OR SubmissionDate >= @StartDate)
        AND (@EndDate IS NULL OR SubmissionDate <= @EndDate)
        AND (@ClaimType IS NULL OR ClaimType = @ClaimType)
        AND (@ClaimStatus IS NULL OR ClaimStatus = @ClaimStatus);
END;
GO


/* High-risk human-review queue */
CREATE OR ALTER PROCEDURE analytics.usp_HighRiskClaims
    @TopN INT = 50,
    @MinimumRiskScore DECIMAL(8,4) = 0.70
AS
BEGIN
    SET NOCOUNT ON;

    IF @TopN < 1
        SET @TopN = 50;

    SELECT TOP (@TopN)
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
        HighCostFlag,
        SLABreachFlag
    FROM analytics.vw_ReviewQueue
    WHERE ProviderRiskScore >= @MinimumRiskScore
    ORDER BY
        CASE ReviewPriority
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            ELSE 4
        END,
        EstimatedLeakageAmount DESC;
END;
GO