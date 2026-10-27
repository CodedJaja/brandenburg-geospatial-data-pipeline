# IRIS-SIG-07 | Brandenburg LUIS planning-notice harvester

## Status and provenance
The assignment specifies `https://luis.brandenburg.de/bauleitplanung` and HTML ingestion pattern B. A web-access check on 2026-10-27 returned an inaccessible/error response; the current site's HTML structure, publication dates, pagination and authorization conditions **could not be verified**. Consequently the submitted implementation is **fixture-tested, not a verified live production scraper**. Sample records are fictional examples and must never be represented as public notices. Do not bypass access controls.

## Purpose
Identify candidate solar-park and data-centre planning notices relevant to Brandenburg. The term *hyperscale* cannot be established from the keyword `Rechenzentrum` alone: all such records are flagged `hyperscale_unverified` and require manual confirmation. `confirmed_brandenburg` means structured fixture/site metadata explicitly declares Brandenburg; it does not prove inclusion in a narrower Berlin metropolitan halo. Actual halo boundaries must be agreed and checked spatially before operational use.

## Setup
Python 3.11+; PostgreSQL 16 with PostGIS 3.4 for database mode.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pytest -q
python harvester.py --fixture fixtures/sample.html --output sample_output.json
```

Optional database:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME'
psql "$DATABASE_URL" -f schema.sql
python harvester.py --fixture fixtures/sample.html --output sample_output.json --load
psql "$DATABASE_URL" -f validation.sql
```

Only after authorized source inspection and selector verification, opt in to `python harvester.py --live --output live_output.json`. The host is restricted to `luis.brandenburg.de`; requests use timeout, retries and HTTP error handling. The live mode currently fetches **one HTML page** and is not certified to cover pagination or JS-rendered content.

## Extraction and mapping
Candidate notices must contain both a planning term and a solar/DC term. Each candidate retains source ID (HTML `data-id` or deterministic hash of URL+title), title, publication date (if parseable), URL, municipality and state metadata when present. Missing fields are explicitly flagged. Duplicate keys within an HTML page are removed; database uniqueness plus `ON CONFLICT DO UPDATE` ensures idempotent re-runs. Missing new dates or geometries do not overwrite previously populated values. Data are staged as candidates rather than asserted projects.

Geometry is **NULL by default**: municipal names alone do not justify a fabricated point. If authoritative WGS84 coordinates become available, `set_geometry` validates the bounds and transforms them to EPSG:25832 via pyproj. Do not assign municipality-centroid points without clearly recording their lower positional accuracy and provenance. Geographic acceptance beyond state-level requires a formally supplied halo polygon and PostGIS `ST_Intersects` filtering.

## Limitations and remaining production work
1. Verify a currently accessible, legally usable official Brandenburg planning-notice source or alternative and capture real HTML fixtures.
2. Confirm real selectors, notice-level stable IDs, date semantics, geographic metadata, and document links.
3. Implement pagination/incremental watermarks or sitemap discovery only after source inspection; add rate limiting and robots/terms review.
4. Add authoritative municipality/parcel geocoding with accuracy classes and Berlin–Brandenburg halo boundary polygon.
5. Validate actual hyperscale capacity indicators (e.g., MW) and classify DC notices by evidence, not keywords alone.
6. Integration-test PostgreSQL/PostGIS with a disposable test DB; current tests cover offline parsing and transformation only.
7. Add observability, alerts, retries for DB outages, and scheduler before deployment.

## Quality report
Fixture: 5 HTML notice blocks; 3 unique candidate signals (2 solar, 1 DC); 1 irrelevant excluded; 1 duplicate excluded; 1 missing date; 1 geography unresolved; 3 NULL geometries; 1 DC hyperscale status unverified. These counts describe **synthetic fixtures**, not real planning activity.
