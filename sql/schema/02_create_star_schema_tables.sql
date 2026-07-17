USE HealthInsuranceClaimsDW;
GO

/* =========================================================
   DIMENSION TABLES
   ========================================================= */

IF OBJECT_ID('dim.[Date]', 'U') IS NULL
BEGIN
    CREATE TABLE dim.[Date] (
        DateKey INT NOT NULL,
        FullDate DATE NOT NULL,
        CalendarYear SMALLINT NOT NULL,
        CalendarQuarter TINYINT NOT NULL,
        MonthNumber TINYINT NOT NULL,
        MonthName VARCHAR(15) NOT NULL,
        YearMonth CHAR(7) NOT NULL,
        DayOfWeekName VARCHAR(15) NOT NULL,
        IsWeekend BIT NOT NULL,

        CONSTRAINT PK_DimDate
            PRIMARY KEY (DateKey),

        CONSTRAINT UQ_DimDate_FullDate
            UNIQUE (FullDate)
    );
END;
GO


IF OBJECT_ID('dim.Beneficiary', 'U') IS NULL
BEGIN
    CREATE TABLE dim.Beneficiary (
        BeneficiaryKey BIGINT IDENTITY(1,1) NOT NULL,
        BeneID VARCHAR(50) NOT NULL,

        CONSTRAINT PK_DimBeneficiary
            PRIMARY KEY (BeneficiaryKey),

        CONSTRAINT UQ_DimBeneficiary_BeneID
            UNIQUE (BeneID)
    );
END;
GO


IF OBJECT_ID('dim.[Plan]', 'U') IS NULL
BEGIN
    CREATE TABLE dim.[Plan] (
        PlanKey INT IDENTITY(1,1) NOT NULL,
        PlanID VARCHAR(20) NOT NULL,
        PlanName VARCHAR(100) NULL,
        DeductibleRate DECIMAL(8,4) NULL,
        CopayRate DECIMAL(8,4) NULL,
        CoverageTier VARCHAR(30) NULL,

        CONSTRAINT PK_DimPlan
            PRIMARY KEY (PlanKey),

        CONSTRAINT UQ_DimPlan_PlanID
            UNIQUE (PlanID)
    );
END;
GO


IF OBJECT_ID('dim.Provider', 'U') IS NULL
BEGIN
    CREATE TABLE dim.Provider (
        ProviderKey BIGINT IDENTITY(1,1) NOT NULL,
        ProviderID VARCHAR(50) NOT NULL,

        CONSTRAINT PK_DimProvider
            PRIMARY KEY (ProviderKey),

        CONSTRAINT UQ_DimProvider_ProviderID
            UNIQUE (ProviderID)
    );
END;
GO


IF OBJECT_ID('dim.ClaimStatus', 'U') IS NULL
BEGIN
    CREATE TABLE dim.ClaimStatus (
        ClaimStatusKey TINYINT IDENTITY(1,1) NOT NULL,
        ClaimStatus VARCHAR(30) NOT NULL,
        StatusGroup VARCHAR(30) NULL,
        StatusSortOrder TINYINT NULL,
        IsOpen BIT NOT NULL,

        CONSTRAINT PK_DimClaimStatus
            PRIMARY KEY (ClaimStatusKey),

        CONSTRAINT UQ_DimClaimStatus_Status
            UNIQUE (ClaimStatus)
    );
END;
GO


IF OBJECT_ID('dim.DenialReason', 'U') IS NULL
BEGIN
    CREATE TABLE dim.DenialReason (
        DenialReasonKey SMALLINT IDENTITY(1,1) NOT NULL,
        DenialReason VARCHAR(50) NOT NULL,
        DenialDescription VARCHAR(250) NULL,
        BusinessOwner VARCHAR(100) NULL,

        CONSTRAINT PK_DimDenialReason
            PRIMARY KEY (DenialReasonKey),

        CONSTRAINT UQ_DimDenialReason_Reason
            UNIQUE (DenialReason)
    );
END;
GO


IF OBJECT_ID('dim.[Policy]', 'U') IS NULL
BEGIN
    CREATE TABLE dim.[Policy] (
        PolicyKey BIGINT IDENTITY(1,1) NOT NULL,
        PolicyID VARCHAR(50) NOT NULL,
        BeneficiaryKey BIGINT NOT NULL,
        PlanKey INT NOT NULL,

        CONSTRAINT PK_DimPolicy
            PRIMARY KEY (PolicyKey),

        CONSTRAINT UQ_DimPolicy_PolicyID
            UNIQUE (PolicyID),

        CONSTRAINT FK_DimPolicy_Beneficiary
            FOREIGN KEY (BeneficiaryKey)
            REFERENCES dim.Beneficiary(BeneficiaryKey),

        CONSTRAINT FK_DimPolicy_Plan
            FOREIGN KEY (PlanKey)
            REFERENCES dim.[Plan](PlanKey)
    );
END;
GO


/* =========================================================
   FACT TABLE
   ========================================================= */

IF OBJECT_ID('fact.[Claim]', 'U') IS NULL
BEGIN
    CREATE TABLE fact.[Claim] (
        ClaimFactKey BIGINT IDENTITY(1,1) NOT NULL,

        ClaimKey VARCHAR(100) NOT NULL,
        ClaimID VARCHAR(100) NOT NULL,
        ClaimType VARCHAR(20) NOT NULL,

        BeneficiaryKey BIGINT NOT NULL,
        PolicyKey BIGINT NOT NULL,
        PlanKey INT NOT NULL,
        ProviderKey BIGINT NOT NULL,
        ClaimStatusKey TINYINT NOT NULL,
        DenialReasonKey SMALLINT NULL,

        ClaimFromDateKey INT NOT NULL,
        ClaimThruDateKey INT NOT NULL,
        SubmissionDateKey INT NOT NULL,
        DecisionDateKey INT NULL,
        PaymentDateKey INT NULL,
        AnalysisDateKey INT NOT NULL,

        PaymentStatus VARCHAR(30) NOT NULL,
        PreauthStatus VARCHAR(30) NOT NULL,
        ReviewPriority VARCHAR(20) NOT NULL,
        QueueName VARCHAR(50) NOT NULL,
        AdjusterID VARCHAR(30) NOT NULL,
        DataProvenance VARCHAR(100) NOT NULL,

        DocumentsCompleteFlag BIT NOT NULL,
        PolicyActiveFlag BIT NOT NULL,
        TreatmentCoveredFlag BIT NOT NULL,
        WaitingPeriodFlag BIT NOT NULL,
        PreauthRequiredFlag BIT NOT NULL,
        SLABreachFlag BIT NOT NULL,
        ManualReviewFlag BIT NOT NULL,
        DuplicateIndicator BIT NOT NULL,
        HighCostFlag BIT NOT NULL,
        FraudAlertFlag BIT NOT NULL,

        BilledAmount DECIMAL(18,2) NOT NULL,
        EligibleAmount DECIMAL(18,2) NOT NULL,
        DeductibleAmount DECIMAL(18,2) NOT NULL,
        CopayAmount DECIMAL(18,2) NOT NULL,
        NonPayableAmount DECIMAL(18,2) NOT NULL,
        AdjustmentAmount DECIMAL(18,2) NOT NULL,
        ApprovedAmount DECIMAL(18,2) NOT NULL,
        PaidAmount DECIMAL(18,2) NOT NULL,
        SourceCMSPaymentAmount DECIMAL(18,2) NOT NULL,
        EstimatedLeakageAmount DECIMAL(18,2) NOT NULL,

        TurnaroundDays INT NOT NULL,
        SLATargetDays SMALLINT NOT NULL,
        ProviderRiskScore DECIMAL(8,4) NOT NULL,

        CONSTRAINT PK_FactClaim
            PRIMARY KEY (ClaimFactKey),

        CONSTRAINT UQ_FactClaim_ClaimKey
            UNIQUE (ClaimKey),

        CONSTRAINT FK_FactClaim_Beneficiary
            FOREIGN KEY (BeneficiaryKey)
            REFERENCES dim.Beneficiary(BeneficiaryKey),

        CONSTRAINT FK_FactClaim_Policy
            FOREIGN KEY (PolicyKey)
            REFERENCES dim.[Policy](PolicyKey),

        CONSTRAINT FK_FactClaim_Plan
            FOREIGN KEY (PlanKey)
            REFERENCES dim.[Plan](PlanKey),

        CONSTRAINT FK_FactClaim_Provider
            FOREIGN KEY (ProviderKey)
            REFERENCES dim.Provider(ProviderKey),

        CONSTRAINT FK_FactClaim_Status
            FOREIGN KEY (ClaimStatusKey)
            REFERENCES dim.ClaimStatus(ClaimStatusKey),

        CONSTRAINT FK_FactClaim_DenialReason
            FOREIGN KEY (DenialReasonKey)
            REFERENCES dim.DenialReason(DenialReasonKey),

        CONSTRAINT FK_FactClaim_ClaimFromDate
            FOREIGN KEY (ClaimFromDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT FK_FactClaim_ClaimThruDate
            FOREIGN KEY (ClaimThruDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT FK_FactClaim_SubmissionDate
            FOREIGN KEY (SubmissionDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT FK_FactClaim_DecisionDate
            FOREIGN KEY (DecisionDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT FK_FactClaim_PaymentDate
            FOREIGN KEY (PaymentDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT FK_FactClaim_AnalysisDate
            FOREIGN KEY (AnalysisDateKey)
            REFERENCES dim.[Date](DateKey),

        CONSTRAINT CK_FactClaim_FinancialHierarchy
            CHECK (
                BilledAmount >= EligibleAmount
                AND EligibleAmount >= ApprovedAmount
                AND ApprovedAmount >= PaidAmount
            ),

        CONSTRAINT CK_FactClaim_NonNegativeAmounts
            CHECK (
                BilledAmount >= 0
                AND EligibleAmount >= 0
                AND DeductibleAmount >= 0
                AND CopayAmount >= 0
                AND NonPayableAmount >= 0
                AND AdjustmentAmount >= 0
                AND ApprovedAmount >= 0
                AND PaidAmount >= 0
                AND EstimatedLeakageAmount >= 0
            )
    );
END;
GO


SELECT
    s.name AS SchemaName,
    t.name AS TableName
FROM sys.tables t
INNER JOIN sys.schemas s
    ON s.schema_id = t.schema_id
WHERE s.name IN ('dim', 'fact')
ORDER BY
    s.name,
    t.name;
GO