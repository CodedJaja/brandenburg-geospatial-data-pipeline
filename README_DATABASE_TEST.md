# IRIS-SIG-07 | PostgreSQL/PostGIS Database Integration and Validation

## Overview

This document describes the local PostgreSQL/PostGIS integration testing workflow for the Brandenburg LUIS Planning-Notice Harvester.

The database uses **PostgreSQL 16 and PostGIS 3.4**, running in Docker Desktop with Linux containers.

Unlike a mock database, this environment executes actual SQL statements against a running PostgreSQL/PostGIS instance.

The database is intended for **disposable local testing only**, not production. Its credentials must not be reused for real or shared systems.

## 1. Prerequisites

- Docker Desktop installed and running with Linux containers.
- Python 3.11 or later.
- Project Python virtual environment activated.
- Project files available in the `iris_sig07` directory.
- Required Python dependencies installed using `requirements.txt`.

The repository includes:

- `docker-compose.yml` — local PostgreSQL/PostGIS container configuration.
- `schema.sql` — database schema.
- `validation.sql` — SQL data-quality validation queries.
- `test_db_integration.py` — automated database integration and idempotency test.
- `harvester.py` — HTML extraction and database ingestion pipeline.

## 2. Start the PostgreSQL/PostGIS Database

Open the project directory in VS Code and launch a PowerShell terminal.

Start the container:

```powershell
docker compose up -d
```

Check its status:

```powershell
docker compose ps
```

The PostGIS service should report `Up (healthy)` once initialization is complete.

The database is exposed locally on port `55432` to avoid conflicts with an existing PostgreSQL installation.

## 3. Configure the Database Connection

In the same PowerShell terminal, run:

```powershell
$env:DATABASE_URL = "postgresql://iris_test:local_test_only@127.0.0.1:55432/iris_test"
```

This sets the connection string for the current PowerShell session.

The credentials are exclusively for the disposable local development database.

## 4. Run Automated Integration Tests

Execute:

```powershell
python -m pytest -v test_db_integration.py
```

**Observed result:**

```text
test_db_integration.py::test_ingest_twice_is_idempotent PASSED

1 passed
```

The integration test verifies repeated ingestion of fixture records using the same database keys.

**Safety note:** The integration test deletes records whose `source_id` begins with `fixture-` in the configured database. Never run it against a production or shared database.

Run the complete automated test suite:

```powershell
python -m pytest -v
```

**Observed result:**

```text
6 passed
```

This includes five original Python tests and one database integration test.

## 5. Load Fixture Records into PostgreSQL

Execute:

```powershell
python harvester.py --fixture fixtures/sample.html --output output.json --load
```

The synthetic fixture produces three unique candidate records.

Verify the stored records:

```powershell
docker compose exec -T postgis psql -U iris_test -d iris_test -c "SELECT source_id, signal_type, geo_status FROM iris_staging.signal_ingest ORDER BY source_id;"
```

**Observed records:**

| Source ID | Signal type | Geographic status |
|---|---|---|
| `fixture-bb-101` | `solar_park` | `confirmed_brandenburg` |
| `fixture-bb-102` | `hyperscale_dc_inquiry` | `confirmed_brandenburg` |
| `fixture-unknown` | `solar_park` | `unresolved` |

Total stored records: **3**

These records are fictional test examples, not verified live Brandenburg planning notices.

## 6. Verify Idempotency and Duplicate Prevention

To test repeat loading manually, rerun:

```powershell
python harvester.py --fixture fixtures/sample.html --output output.json --load
```

Then check the number of records:

```powershell
docker compose exec -T postgis psql -U iris_test -d iris_test -c "SELECT COUNT(*) FROM iris_staging.signal_ingest;"
```

For the three-record fixture dataset, the expected count after repeated loading is still three.

To check for duplicate ingestion keys:

```powershell
docker compose exec -T postgis psql -U iris_test -d iris_test -c "SELECT source_system, source_id, signal_type, COUNT(*) FROM iris_staging.signal_ingest GROUP BY source_system, source_id, signal_type HAVING COUNT(*) > 1;"
```

**Observed result:**

```text
(0 rows)
```

The integration test passed, and the duplicate-key query found no duplicate records.

## 7. Execute Complete SQL Validation

Run:

```powershell
Get-Content .\validation.sql | docker compose exec -T postgis psql -U iris_test -d iris_test
```

All six SQL validation queries executed successfully.

### Observed SQL Validation Results

| Validation | Result |
|---|---|
| Total ingested fixture records | 3 |
| Duplicate ingestion keys | 0 |
| Missing publication dates | 1 |
| Unresolved geometries | 3 |
| Non-NULL geometry SRIDs returned | 0 |
| Records containing quality flags | 2 |

### Quality Flags

| Source ID | Quality flags |
|---|---|
| `fixture-bb-102` | `hyperscale_unverified` |
| `fixture-unknown` | `publication_date_missing_or_invalid`, `geography_unverified` |

The missing publication date and unresolved geographic information are intentional fixture-quality scenarios.

`confirmed_brandenburg` indicates state-level metadata, not verified coordinates. All three fixture records have unresolved geometries.

The zero-row SRID result indicates that no non-NULL geometry was available for SRID validation.

## 8. Data Quality and Interpretation

The validation demonstrates that the local pipeline can:

- Extract synthetic HTML planning-notice candidates.
- Store candidate records in PostgreSQL/PostGIS.
- Reprocess records idempotently under the tested conditions.
- Preserve missing-date and geographic-quality information.
- Identify records requiring additional manual verification.
- Execute database quality and duplicate-key checks.

The `hyperscale_unverified` flag is particularly important because the presence of a data-centre planning notice does not independently establish hyperscale capacity.

## 9. Limitations

This testing was performed using synthetic HTML fixtures.

The following capabilities remain unverified or incomplete:

1. Successful live harvesting from the Brandenburg LUIS website.
2. Complete pagination and dynamic website coverage.
3. Verified notice-level identifiers and publication-date semantics from the live source.
4. Non-NULL point geometry insertion and stored EPSG:25832 SRID validation.
5. Berlin–Brandenburg metropolitan halo spatial filtering.
6. Production deployment, scheduling, and operational monitoring.

These limitations do not invalidate the successful local tests but prevent the implementation from being described as a fully verified production harvester.

## 10. Stop or Remove the Test Database

To stop and remove the containers while retaining the database volume:

```powershell
docker compose down
```

To remove the containers **and permanently delete the disposable test database volume**:

```powershell
docker compose down -v
```

Use the second command only when the local test data is no longer needed.

## 11. Final Validation Summary

**Environment:** Windows, Python 3.14.2, pytest 9.1.1, Docker Desktop, PostgreSQL 16, PostGIS 3.4.

**Verified local outcomes:**

- Six automated tests passed.
- PostgreSQL/PostGIS container started and reported healthy.
- Three synthetic fixture records were stored successfully.
- Database integration and idempotency test passed.
- Zero duplicate ingestion keys were detected.
- All six SQL validation queries executed successfully.
- Missing dates, unresolved geometries, and quality flags were documented.

**Conclusion:** The fixture-based pipeline successfully passed local Python and PostgreSQL/PostGIS validation. Live-source extraction and spatial verification remain documented limitations requiring additional source access and authoritative geographic data.