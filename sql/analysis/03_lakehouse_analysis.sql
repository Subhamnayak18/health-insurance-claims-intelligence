-- Source-derived CMS measures; no simulated approval or fraud metrics.
SELECT CLAIM_MONTH, CLAIM_TYPE, CLAIM_COUNT, CLAIM_PAYMENT_AMOUNT,
       CLAIM_PAYMENT_AMOUNT / NULLIF(CLAIM_COUNT, 0) AS AveragePaymentPerClaim
FROM lake.monthly_claims
ORDER BY CLAIM_MONTH, CLAIM_TYPE;

SELECT TOP (20) p.PROVIDER_ID_TYPE, p.PROVIDER_ID, s.CLAIM_TYPE,
       s.CLAIM_COUNT, s.CLAIM_PAYMENT_AMOUNT
FROM lake.provider_claims s
JOIN lake.dim_provider p ON p.PROVIDER_KEY = s.PRIMARY_PROVIDER_KEY
ORDER BY s.CLAIM_PAYMENT_AMOUNT DESC, s.PRIMARY_PROVIDER_KEY;

-- Header totals must equal monthly totals and provider-attributed totals.
IF (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.fact_claim) <>
   (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.monthly_claims)
    THROW 51000, 'Monthly payment reconciliation failed', 1;
IF (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.fact_claim) <>
   (SELECT SUM(CLAIM_PAYMENT_AMOUNT) FROM lake.provider_claims)
    THROW 51000, 'Provider payment reconciliation failed', 1;
