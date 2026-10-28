"""Optional integration test against disposable local PostGIS (requires DATABASE_URL)."""
import os
from pathlib import Path
import pytest

psycopg = pytest.importorskip('psycopg')
from harvester import ingest, parse_html

@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='DATABASE_URL not set')
def test_ingest_twice_is_idempotent():
    fixture = Path(__file__).parent / 'fixtures' / 'sample.html'
    records = parse_html(fixture.read_text(encoding='utf-8'))
    keys = [(r['source_system'], r['source_id'], r['signal_type']) for r in records]
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM iris_staging.signal_ingest WHERE source_system = %s AND source_id LIKE %s', ('brandenburg_luis', 'fixture-%'))
        conn.commit()
        ingest(conn, records)
        ingest(conn, records)
        with conn.cursor() as cur:
            cur.execute('SELECT source_system, source_id, signal_type FROM iris_staging.signal_ingest WHERE source_system = %s AND source_id LIKE %s', ('brandenburg_luis', 'fixture-%'))
            assert sorted(cur.fetchall()) == sorted(keys)
            cur.execute('SELECT COUNT(*) FROM iris_staging.signal_ingest WHERE geom IS NOT NULL AND ST_SRID(geom) <> 25832')
            assert cur.fetchone()[0] == 0
