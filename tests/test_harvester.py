from pathlib import Path
import pytest
from harvester import parse_html, parse_date, set_geometry, stable_id
FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/sample.html'

def test_parser_filters_and_deduplicates():
    rows = parse_html(FIXTURE.read_text())
    assert len(rows) == 3
    assert {r['signal_type'] for r in rows} == {'solar_park', 'hyperscale_dc_inquiry'}
    assert len({(r['source_id'],r['signal_type']) for r in rows}) == 3

def test_date_and_quality_flags():
    rows = parse_html(FIXTURE.read_text())
    assert rows[0]['publication_date'] == '2026-09-15'
    assert rows[2]['geo_status'] == 'unresolved'
    assert 'publication_date_missing_or_invalid' in rows[2]['quality_flags']
    assert parse_date('32.13.2026') is None

def test_coordinate_validation_and_transform():
    row = {}
    set_geometry(row, 13.06, 52.4)
    assert row['geom_wkt'].startswith('POINT(')
    with pytest.raises(ValueError):
        set_geometry({}, 0, 0)

def test_stable_ids():
    assert stable_id('https://x/a', 'Title') == stable_id('https://x/a', 'title')

def test_repeat_parser_is_deterministic():
    html = FIXTURE.read_text()
    assert parse_html(html) == parse_html(html)
