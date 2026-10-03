# Local setup

Run commands from the repository root. Python 3.11, Java 17, Spark 3.5.6 and Delta 3.3.2 are the selected runtime. See the [Delta compatibility matrix](https://docs.delta.io/releases/) and [Spark requirements](https://spark.apache.org/docs/3.5.6/).

## Existing Windows workspace

The original `.venv` points at a removed Python installation and is preserved. The upgrade uses `.venv-spark311`; Java and Windows Hadoop helpers live in ignored `.runtime` directories. In a new PowerShell window:

```powershell
$env:JAVA_HOME = (Get-ChildItem .runtime/java -Directory | Select-Object -First 1).FullName
$env:HADOOP_HOME = Join-Path (Get-Location) '.runtime/hadoop'
$env:PATH = "$env:HADOOP_HOME\bin;$env:JAVA_HOME\bin;$env:PATH"
.\.venv-spark311\Scripts\Activate.ps1
python -m pytest -q
$env:PYSPARK_SUBMIT_ARGS = '--driver-memory 3g pyspark-shell'
python -m src.pipeline
```

For a fresh clone, install [Microsoft OpenJDK 17](https://learn.microsoft.com/en-us/java/openjdk/download) and Python 3.11, then follow the README environment commands. Hadoop on Windows needs native helpers as described by [Apache](https://cwiki.apache.org/confluence/spaces/HADOOP2/pages/120730292/WindowsProblems). The local run uses community Hadoop 3.3.5 helpers from [cdarlint/winutils](https://github.com/cdarlint/winutils/tree/master/hadoop-3.3.5/bin). They are not committed or downloaded automatically by project code. Use a trusted native build or a Linux runtime for another installation.

## Small run without downloading CMS data

```powershell
python -m src.pipeline --raw-dir tests/fixtures --data-dir .runtime/demo-lake
python -m src.pipeline --raw-dir tests/fixtures --data-dir .runtime/demo-lake
python -m src.export_gold --data-dir .runtime/demo-lake --output-dir .runtime/demo-export
```

The fixture is hand-written test data: four lines and three claims, including a negative adjustment. Its counts are never reported as CMS dataset results.

## Original pandas workflow

The original scripts remain runnable as modules. The first four steps also need the beneficiary CSV files from 2015–2025 in the raw folder.

```powershell
python -m src.validation.profile_raw_data
python -m src.validation.build_cleaning_plan
python -m src.data_cleaning.clean_cms_data
python -m src.validation.validate_clean_data
python -m src.transformations.build_claim_header
python -m src.data_generation.generate_claim_operations
python -m src.transformations.prepare_excel_exports
python -m src.validation.build_sql_column_profile
```

These commands regenerate the original `data/processed` outputs and corresponding audit documents. They are separate from the lakehouse. The operational simulation uses a fixed seed but depends on input ordering; it is not an incremental source of real claim decisions. Keep its existing outputs if you want the existing Excel/Power BI report to retain the same simulated results.
