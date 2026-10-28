# IRIS-SIG-07 | Brandenburg LUIS Planning-Notice Harvester

## Status and Provenance

The assignment specifies [Brandenburg LUIS Bauleitplanung](https://luis.brandenburg.de/bauleitplanung) and HTML ingestion pattern B.

A web-access check on 2026-10-27 returned an inaccessible/error response. The current site's HTML structure, publication dates, pagination, and authorization conditions could not be verified.

Consequently, the implementation is **fixture-tested and locally database-validated, not a verified live production scraper**.

Sample records are fictional examples and must never be represented as actual public planning notices. Access controls must not be bypassed.

## Purpose

Identify candidate solar-park and data-centre planning notices relevant to Brandenburg.

The term *hyperscale* cannot be established from the keyword `Rechenzentrum` alone. Such records are flagged `hyperscale_unverified` and require manual confirmation.

`confirmed_brandenburg` means structured fixture/site metadata explicitly declares Brandenburg. It does not establish inclusion in the narrower Berlin metropolitan halo.

Actual metropolitan halo boundaries must be agreed upon and checked spatially before operational use.

## Setup

**Requirements:**
- Python 3.11+
- PostgreSQL 16 with PostGIS 3.4 for database integration
- Docker Desktop for the containerized database testing workflow

### Python Environment

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run automated tests:

```powershell
python -m pytest -v
```

Run the fixture-based harvester:

```powershell
python harvester.py --fixture fixtures/sample.html --output output.json
```

### PostgreSQL/PostGIS Database Setup

Start Docker Desktop and confirm the Docker Engine is running.

Start the PostgreSQL/PostGIS container:

```powershell
docker compose up -d
```

Verify container health:

```powershell
docker compose ps
```

Configure the local test database connection:

```powershell
$env:DATABASE_URL = "postgresql://iris_test:local_test_only@127.0.0.1:55432/iris_test"
```

These credentials are for the disposable local development database only.

Run the database integration test:

```powershell
python -m pytest -v test_db_integration.py
```

Load fixture records into the database:

```powershell
python harvester.py --fixture fixtures/sample.html --output output.json --load
```

Execute the SQL validation script:

```powershell
Get-Content .\validation.sql | docker compose exec -T postgis psql -U iris_test -d iris_test
```

For additional instructions, see `README_DATABASE_TEST.md`.

### Live Mode

Only after authorized source inspection and selector verification, opt in to:

```bash
python harvester.py --live --output live_output.json
```

The host is restricted to `luis.brandenburg.de`. Requests use timeout, retries, and HTTP error handling.

Live mode currently fetches **one HTML page** and is not certified to cover pagination or JavaScript-rendered content.

## Extraction and Mapping

Candidate notices must contain both a planning term and a solar/data-centre term.

Each candidate retains:

- Source ID (HTML `data-id` or deterministic hash of URL and title)
- Title
- Publication date, if parseable
- Source URL
- Municipality and state metadata, when present
- Geographic status and quality flags

Missing fields are explicitly flagged.

Duplicate keys within an HTML page are removed. Database uniqueness and `ON CONFLICT DO UPDATE` support idempotent ingestion.

Missing new dates or geometries do not overwrite previously populated values.

Records are staged as candidate signals rather than asserted development projects.

### Geometry Handling

Geometry is **NULL by default** because municipal names alone do not justify fabricated coordinates.

If authoritative WGS84 coordinates become available, `set_geometry` validates their bounds and transforms them into EPSG:25832 using pyproj.

Municipality-centroid points must not be assigned without recording their positional accuracy and provenance.

Geographic acceptance beyond state-level requires a formally supplied metropolitan halo polygon and PostGIS `ST_Intersects` filtering.

The current synthetic fixture records do not contain verified point geometries.

## Automated Testing

The project was tested locally using Python 3.14.2, pytest 9.1.1, Docker Desktop, PostgreSQL 16, and PostGIS 3.4.

**Automated test results:**

| Test category | Result |
|---|---|
| Python extraction and transformation tests | 5 passed |
| PostgreSQL/PostGIS integration and idempotency test | 1 passed |
| Total automated tests | **6 passed, 0 failed** |

The integration test verifies repeated ingestion into a disposable PostgreSQL/PostGIS database without duplicate ingestion keys.

## Database Validation Results

The complete `validation.sql` script was executed successfully against the local PostgreSQL/PostGIS database.

| Validation metric | Observed result |
|---|---|
| Total stored synthetic candidate records | 3 |
| Duplicate ingestion keys | 0 |
| Missing publication dates | 1 |
| Unresolved geometries | 3 |
| Non-NULL geometry SRIDs returned | 0 |
| Records containing quality flags | 2 |

### Ingested Fixture Records

| Source ID | Signal type | Geographic status |
|---|---|---|
| `fixture-bb-101` | `solar_park` | `confirmed_brandenburg` |
| `fixture-bb-102` | `hyperscale_dc_inquiry` | `confirmed_brandenburg` |
| `fixture-unknown` | `solar_park` | `unresolved` |

The zero-duplicate result supports successful idempotent ingestion under the tested fixture conditions.

The absence of non-NULL geometries means that spatial geometry insertion and stored EPSG:25832 SRIDs have not yet been demonstrated with real coordinates.

## Limitations and Remaining Production Work

1. Verify a currently accessible, legally usable official Brandenburg planning-notice source or justified alternative and capture representative real HTML fixtures.
2. Confirm actual selectors, notice-level stable identifiers, date semantics, geographic metadata, and document links.
3. Implement pagination, incremental watermarks, or sitemap discovery after source inspection, including rate limiting and robots/terms review.
4. Add authoritative municipality/parcel geocoding with accuracy classes and a Berlin–Brandenburg metropolitan halo boundary polygon.
5. Validate hyperscale capacity indicators, such as megawatt capacity, and classify data-centre notices using supporting evidence rather than keywords alone.
6. Extend PostGIS integration tests to cover non-NULL geometry insertion, EPSG:25832 SRID verification, and spatial filtering. The local fixture-based database integration and idempotency tests have already passed.
7. Add operational observability, alerts, database-outage handling, and scheduling before deployment.

## Quality Report

The synthetic fixture contains five HTML notice blocks:

| Quality measure | Count |
|---|---|
| Total HTML notice blocks | 5 |
| Unique candidate signals | 3 |
| Solar-park candidates | 2 |
| Data-centre candidates | 1 |
| Irrelevant notice excluded | 1 |
| Duplicate notice excluded | 1 |
| Missing publication date | 1 |
| Record with unresolved geographic status | 1 |
| Records with NULL geometries | 3 |
| Data-centre records with unverified hyperscale classification | 1 |

**Interpretation:** One record has an unresolved geographic status, while all three lack resolved point geometries. These are different quality measures.

All counts describe synthetic fixtures and local testing outcomes, not actual Brandenburg planning activity.

## Submission Scope

This repository provides a fixture-based Python extraction pipeline, PostgreSQL/PostGIS staging integration, idempotent loading, automated tests, sample outputs, SQL validation queries, and documented quality limitations.

The implementation has passed its local automated and database validation tests. Live-source coverage, metropolitan halo filtering, and non-NULL spatial geometry validation remain outside the demonstrated scope.
