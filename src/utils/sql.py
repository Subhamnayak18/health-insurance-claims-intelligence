import os

import pyodbc


def create_connection():
    configured = os.environ.get("CLAIMS_SQL_CONNECTION_STRING")
    if configured:
        return pyodbc.connect(configured, autocommit=False, timeout=15)
    drivers = pyodbc.drivers()
    driver = next((name for name in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"] if name in drivers), None)
    if driver is None:
        raise RuntimeError("Install Microsoft ODBC Driver 18 for SQL Server")
    # Local Windows development only. Azure must supply an encrypted connection.
    return pyodbc.connect(
        f"DRIVER={{{driver}}};SERVER=localhost;DATABASE=HealthInsuranceClaimsDW;"
        "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;",
        autocommit=False, timeout=15,
    )
