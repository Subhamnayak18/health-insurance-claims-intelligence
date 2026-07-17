USE master;
GO

IF DB_ID('HealthInsuranceClaimsDW') IS NULL
BEGIN
    CREATE DATABASE HealthInsuranceClaimsDW;
END;
GO

ALTER DATABASE HealthInsuranceClaimsDW
SET RECOVERY SIMPLE;
GO

USE HealthInsuranceClaimsDW;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'stg'
)
BEGIN
    EXEC('CREATE SCHEMA stg AUTHORIZATION dbo');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'dim'
)
BEGIN
    EXEC('CREATE SCHEMA dim AUTHORIZATION dbo');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'fact'
)
BEGIN
    EXEC('CREATE SCHEMA fact AUTHORIZATION dbo');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'analytics'
)
BEGIN
    EXEC('CREATE SCHEMA analytics AUTHORIZATION dbo');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.schemas
    WHERE name = 'audit'
)
BEGIN
    EXEC('CREATE SCHEMA audit AUTHORIZATION dbo');
END;
GO

SELECT
    DB_NAME() AS DatabaseName,
    name AS SchemaName
FROM sys.schemas
WHERE name IN (
    'stg',
    'dim',
    'fact',
    'analytics',
    'audit'
)
ORDER BY name;
GO