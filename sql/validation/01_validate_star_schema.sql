USE HealthInsuranceClaimsDW;
GO
SET NOCOUNT ON;

DECLARE @SourceRows BIGINT = (SELECT COUNT_BIG(*) FROM stg.ClaimOperations);
DECLARE @FactRows BIGINT = (SELECT COUNT_BIG(*) FROM fact.[Claim]);

IF @SourceRows = 0 OR @SourceRows <> @FactRows
    THROW 51000, 'Staging and fact counts differ or are empty', 1;

IF EXISTS (SELECT CLAIM_KEY FROM stg.ClaimOperations GROUP BY CLAIM_KEY HAVING COUNT(*) > 1)
   OR EXISTS (SELECT ClaimKey FROM fact.[Claim] GROUP BY ClaimKey HAVING COUNT(*) > 1)
    THROW 51000, 'Duplicate claim keys', 1;

IF EXISTS (
    SELECT 1 FROM stg.ClaimOperations s
    FULL JOIN fact.[Claim] f ON f.ClaimKey = s.CLAIM_KEY
    WHERE s.CLAIM_KEY IS NULL OR f.ClaimKey IS NULL
       OR f.BilledAmount <> s.BILLED_AMOUNT
       OR f.ApprovedAmount <> s.APPROVED_AMOUNT
       OR f.PaidAmount <> s.PAID_AMOUNT
)
    THROW 51000, 'Claim keys or financial amounts do not reconcile', 1;

IF EXISTS (
    SELECT 1 FROM fact.[Claim]
    WHERE BilledAmount < EligibleAmount OR EligibleAmount < ApprovedAmount
       OR ApprovedAmount < PaidAmount
)
    THROW 51000, 'Financial hierarchy errors', 1;

IF EXISTS (
    SELECT 1 FROM fact.[Claim] f
    LEFT JOIN dim.Beneficiary b ON b.BeneficiaryKey = f.BeneficiaryKey
    LEFT JOIN dim.[Policy] p ON p.PolicyKey = f.PolicyKey
    LEFT JOIN dim.[Plan] pl ON pl.PlanKey = f.PlanKey
    LEFT JOIN dim.Provider pr ON pr.ProviderKey = f.ProviderKey
    LEFT JOIN dim.ClaimStatus cs ON cs.ClaimStatusKey = f.ClaimStatusKey
    WHERE b.BeneficiaryKey IS NULL OR p.PolicyKey IS NULL OR pl.PlanKey IS NULL
       OR pr.ProviderKey IS NULL OR cs.ClaimStatusKey IS NULL
       OR p.BeneficiaryKey <> f.BeneficiaryKey OR p.PlanKey <> f.PlanKey
)
    THROW 51000, 'Missing or inconsistent dimension relationships', 1;

SELECT @SourceRows AS StagingRows, @FactRows AS FactRows, 'PASS' AS ValidationStatus;
GO
