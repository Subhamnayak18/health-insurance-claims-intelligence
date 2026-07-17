USE HealthInsuranceClaimsDW;
GO

/* 1. Staging versus fact row counts */
SELECT
    (SELECT COUNT(*) FROM stg.ClaimOperations) AS StagingRows,
    (SELECT COUNT(*) FROM fact.[Claim]) AS FactRows;
GO


/* 2. Duplicate claim keys */
SELECT
    COUNT(*) AS DuplicateClaimKeys
FROM (
    SELECT ClaimKey
    FROM fact.[Claim]
    GROUP BY ClaimKey
    HAVING COUNT(*) > 1
) duplicates;
GO


/* 3. Financial hierarchy errors */
SELECT
    COUNT(*) AS FinancialHierarchyErrors
FROM fact.[Claim]
WHERE
    BilledAmount < EligibleAmount
    OR EligibleAmount < ApprovedAmount
    OR ApprovedAmount < PaidAmount;
GO


/* 4. Missing dimension relationships */
SELECT
    SUM(CASE WHEN BeneficiaryKey IS NULL THEN 1 ELSE 0 END)
        AS MissingBeneficiaryKeys,
    SUM(CASE WHEN PolicyKey IS NULL THEN 1 ELSE 0 END)
        AS MissingPolicyKeys,
    SUM(CASE WHEN PlanKey IS NULL THEN 1 ELSE 0 END)
        AS MissingPlanKeys,
    SUM(CASE WHEN ProviderKey IS NULL THEN 1 ELSE 0 END)
        AS MissingProviderKeys,
    SUM(CASE WHEN ClaimStatusKey IS NULL THEN 1 ELSE 0 END)
        AS MissingClaimStatusKeys
FROM fact.[Claim];
GO


/* 5. Financial reconciliation */
SELECT
    source.TotalBilledSource,
    warehouse.TotalBilledWarehouse,
    source.TotalApprovedSource,
    warehouse.TotalApprovedWarehouse,
    source.TotalPaidSource,
    warehouse.TotalPaidWarehouse
FROM (
    SELECT
        SUM(BILLED_AMOUNT) AS TotalBilledSource,
        SUM(APPROVED_AMOUNT) AS TotalApprovedSource,
        SUM(PAID_AMOUNT) AS TotalPaidSource
    FROM stg.ClaimOperations
) source
CROSS JOIN (
    SELECT
        SUM(BilledAmount) AS TotalBilledWarehouse,
        SUM(ApprovedAmount) AS TotalApprovedWarehouse,
        SUM(PaidAmount) AS TotalPaidWarehouse
    FROM fact.[Claim]
) warehouse;
GO


/* 6. Final validation summary */
SELECT
    CASE
        WHEN
            (SELECT COUNT(*) FROM fact.[Claim]) = 514225
            AND (SELECT COUNT(DISTINCT ClaimKey) FROM fact.[Claim]) = 514225
            AND NOT EXISTS (
                SELECT 1
                FROM fact.[Claim]
                WHERE BilledAmount < EligibleAmount
                   OR EligibleAmount < ApprovedAmount
                   OR ApprovedAmount < PaidAmount
            )
        THEN 'PASS'
        ELSE 'FAIL'
    END AS StarSchemaValidationStatus;
GO