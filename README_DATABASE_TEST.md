# IRIS-SIG-07: optional disposable PostGIS validation

This is a **real PostgreSQL 16 / PostGIS 3.4 test database**, not a mock. Requires Docker Desktop running with Linux containers, and the project's Python virtual environment. It is for **local testing only**, not production; the password is deliberately a disposable local test password.

1. Copy `docker-compose.yml`, `schema.sql`, `validation.sql`, and `test_db_integration.py` into the root of your existing `iris_sig07` project (next to `harvester.py`). Keep `fixtures/` and `tests/` unchanged.
2. In VS Code PowerShell in that folder:

```powershell
docker compose up -d
docker compose ps
$env:DATABASE_URL = 'postgresql://iris_test:local_test_only@127.0.0.1:55432/iris_test'
python -m pytest -v test_db_integration.py
python harvester.py --fixture fixtures/sample.html --output output.json --load
docker compose exec -T postgis psql -U iris_test -d iris_test -c 'SELECT COUNT(*) FROM iris_staging.signal_ingest;'
Get-Content validation.sql | docker compose exec -T postgis psql -U iris_test -d iris_test
```

Expected after first load: 3 fixture records; after repeat load: still 3. The integration test deletes **only records whose source_id starts `fixture-`** in the configured database; do not point it at a shared or production database. The SQL validation shows missing dates, unresolved geometries and quality flags; these are expected from the synthetic fixture, not evidence of a failed run. The Docker service uses port 55432 to avoid colliding with any local PostgreSQL installation.

To test repeat loading manually, rerun the `python harvester.py ... --load` command, then check the row count again.

When finished:

```powershell
docker compose down
```

To delete the test database data too:

```powershell
docker compose down -v
```

**Important:** These files were prepared for local execution; no Docker database was started or verified in this environment. Only claim database validation after the commands actually pass on your machine.
