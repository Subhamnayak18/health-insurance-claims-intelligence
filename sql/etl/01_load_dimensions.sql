USE HealthInsuranceClaimsDW;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    /* Date dimension */
    ;WITH AllDates AS (
        SELECT CLAIM_FROM_DATE AS FullDate FROM stg.ClaimOperations
        UNION
        SELECT CLAIM_THRU_DATE FROM stg.ClaimOperations
        UNION
        SELECT SUBMISSION_DATE FROM stg.ClaimOperations
        UNION
        SELECT DECISION_DATE FROM stg.ClaimOperations
        UNION
        SELECT PAYMENT_DATE FROM stg.ClaimOperations
        UNION
        SELECT ANALYSIS_DATE FROM stg.ClaimOperations
    )
    INSERT INTO dim.[Date] (
        DateKey,
        FullDate,
        CalendarYear,
        CalendarQuarter,
        MonthNumber,
        MonthName,
        YearMonth,
        DayOfWeekName,
        IsWeekend
    )
    SELECT
        CONVERT(INT, CONVERT(CHAR(8), FullDate, 112)),
        FullDate,
        YEAR(FullDate),
        DATEPART(QUARTER, FullDate),
        MONTH(FullDate),
        DATENAME(MONTH, FullDate),
        CONVERT(CHAR(7), FullDate, 120),
        DATENAME(WEEKDAY, FullDate),
        CASE
            WHEN DATENAME(WEEKDAY, FullDate)
                 IN ('Saturday', 'Sunday') THEN 1
            ELSE 0
        END
    FROM AllDates d
    WHERE FullDate IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM dim.[Date] existing
          WHERE existing.FullDate = d.FullDate
      );

    /* Beneficiary dimension */
    INSERT INTO dim.Beneficiary (BeneID)
    SELECT DISTINCT s.BENE_ID
    FROM stg.ClaimOperations s
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim.Beneficiary d
        WHERE d.BeneID = s.BENE_ID
    );

    /* Plan dimension */
    INSERT INTO dim.[Plan] (PlanID)
    SELECT DISTINCT s.PLAN_ID
    FROM stg.ClaimOperations s
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim.[Plan] d
        WHERE d.PlanID = s.PLAN_ID
    );

    /* Provider dimension */
    INSERT INTO dim.Provider (ProviderID)
    SELECT DISTINCT s.PRIMARY_PROVIDER_ID
    FROM stg.ClaimOperations s
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim.Provider d
        WHERE d.ProviderID = s.PRIMARY_PROVIDER_ID
    );

    /* Claim-status dimension */
    INSERT INTO dim.ClaimStatus (
        ClaimStatus,
        StatusGroup,
        StatusSortOrder,
        IsOpen
    )
    SELECT DISTINCT
        s.CLAIM_STATUS,
        CASE
            WHEN s.CLAIM_STATUS IN ('PENDING', 'MANUAL_REVIEW')
                THEN 'OPEN'
            ELSE 'CLOSED'
        END,
        CASE s.CLAIM_STATUS
            WHEN 'APPROVED' THEN 1
            WHEN 'PARTIALLY_APPROVED' THEN 2
            WHEN 'PENDING' THEN 3
            WHEN 'MANUAL_REVIEW' THEN 4
            WHEN 'REJECTED' THEN 5
            ELSE 99
        END,
        CASE
            WHEN s.CLAIM_STATUS IN ('PENDING', 'MANUAL_REVIEW')
                THEN 1
            ELSE 0
        END
    FROM stg.ClaimOperations s
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim.ClaimStatus d
        WHERE d.ClaimStatus = s.CLAIM_STATUS
    );

    /* Denial-reason dimension */
    INSERT INTO dim.DenialReason (DenialReason)
    SELECT DISTINCT s.DENIAL_REASON
    FROM stg.ClaimOperations s
    WHERE s.DENIAL_REASON IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM dim.DenialReason d
          WHERE d.DenialReason = s.DENIAL_REASON
      );

    /* Policy dimension */
    INSERT INTO dim.[Policy] (
        PolicyID,
        BeneficiaryKey,
        PlanKey
    )
    SELECT DISTINCT
        s.POLICY_ID,
        b.BeneficiaryKey,
        p.PlanKey
    FROM stg.ClaimOperations s
    INNER JOIN dim.Beneficiary b
        ON b.BeneID = s.BENE_ID
    INNER JOIN dim.[Plan] p
        ON p.PlanID = s.PLAN_ID
    WHERE NOT EXISTS (
        SELECT 1
        FROM dim.[Policy] d
        WHERE d.PolicyID = s.POLICY_ID
    );

    COMMIT TRANSACTION;

    PRINT 'Dimension loading completed successfully.';

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO