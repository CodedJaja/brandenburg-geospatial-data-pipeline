"""IRIS-SIG-07: conservative HTML/fixture ingestion for public planning notices."""
import argparse
import hashlib
import json
import logging
import os
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

LOG = logging.getLogger('iris_sig07')
SOLAR = re.compile(r'\b(?:solarpark|photovoltaik|pv.freifl[aä]chenanlage|solaranlage|freifl[aä]chen.photovoltaik)\b', re.I)
DC = re.compile(r'\b(?:rechenzentrum|data.?cent(?:er|re)|hyperscal(?:e|er))\b', re.I)
PLANNING = re.compile(r'\b(?:bebauungsplan|bauleitplanung|fl[aä]chennutzungsplan|b.plan|aufstellungsbeschluss|offenlage|auslegung)\b', re.I)
DATE_RE = re.compile(r'\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b')
BASE = 'https://luis.brandenburg.de/bauleitplanung'


def parse_date(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def classify(text):
    if not PLANNING.search(text):
        return None
    if SOLAR.search(text):
        return 'solar_park'
    if DC.search(text):
        return 'hyperscale_dc_inquiry'  # candidate only; scale not established by keyword
    return None


def stable_id(url, title):
    return hashlib.sha256((url.strip() + '|' + title.strip().casefold()).encode()).hexdigest()[:32]


def parse_html(html, base_url=BASE):
    """Conservative generic parser; actual site selectors must be verified before live use."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()
    for node in soup.select('article, li.notice, .notice, .planning-item'):
        title_node = node.select_one('h1,h2,h3,h4,.title,a[href]')
        link = node.select_one('a[href]')
        if not title_node or not link:
            continue
        title = title_node.get_text(' ', strip=True)
        text = node.get_text(' ', strip=True)
        kind = classify(text)
        if not kind:
            continue
        url = urljoin(base_url, link.get('href', ''))
        if urlparse(url).scheme not in ('http', 'https'):
            continue
        date_node = node.select_one('time[datetime],time,.date')
        raw_date = (date_node.get('datetime') or date_node.get_text(' ', strip=True)) if date_node else None
        if not raw_date:
            match = DATE_RE.search(text)
            raw_date = match.group(0) if match else None
        published = parse_date(raw_date)
        municipality = node.get('data-municipality') or None
        state = (node.get('data-state') or '').strip()
        # Geographic acceptance requires an explicit Brandenburg signal in structured metadata.
        # Ambiguous records are retained for review but never treated as confirmed in-scope.
        geo_status = 'confirmed_brandenburg' if state.casefold() in ('brandenburg', 'bb') else 'unresolved'
        source_id = node.get('data-id') or stable_id(url, title)
        key = (source_id, kind)
        if key in seen:
            continue
        seen.add(key)
        results.append(dict(source_system='brandenburg_luis', source_id=source_id,
                            signal_type=kind, title=title, publication_date=published,
                            source_url=url, municipality=municipality,
                            state=state or None, geo_status=geo_status,
                            longitude=None, latitude=None, geom_wkt=None,
                            quality_flags=(["publication_date_missing_or_invalid"] if not published else []) +
                                          (["geography_unverified"] if geo_status == 'unresolved' else []) +
                                          (["hyperscale_unverified"] if kind == 'hyperscale_dc_inquiry' else [])))
    return results


def set_geometry(record, longitude, latitude):
    """Transform validated WGS84 coordinates to EPSG:25832; no guessed geocoding."""
    from pyproj import Transformer
    lon, lat = float(longitude), float(latitude)
    if not (5 <= lon <= 16 and 47 <= lat <= 56):
        raise ValueError('Coordinate outside plausible Germany bounding box')
    x, y = Transformer.from_crs(4326, 25832, always_xy=True).transform(lon, lat)
    if not (100000 <= x <= 900000 and 5000000 <= y <= 6500000):
        raise ValueError('Invalid transformed coordinates')
    record.update(longitude=lon, latitude=lat, geom_wkt=f'POINT({x:.3f} {y:.3f})')
    return record


def fetch_html(url, timeout=20):
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'luis.brandenburg.de':
        raise ValueError('Live retrieval restricted to authorized source host')
    session = requests.Session()
    session.headers.update({'User-Agent': 'IRIS-SIG-07 research harvester/1.0 (respectful public access)'})
    session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'])))
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    if 'html' not in response.headers.get('Content-Type', '').lower():
        raise ValueError('Expected HTML content type')
    return response.text


def ingest(conn, records):
    """Idempotent transaction; PostGIS geometry constructed only from verified WKT."""
    sql = '''INSERT INTO iris_staging.signal_ingest
    (source_system,source_id,signal_type,title,publication_date,source_url,municipality,
     state,geo_status,quality_flags,geom,observed_at)
    VALUES (%(source_system)s,%(source_id)s,%(signal_type)s,%(title)s,%(publication_date)s,
      %(source_url)s,%(municipality)s,%(state)s,%(geo_status)s,%(quality_flags)s,
      CASE WHEN %(geom_wkt)s IS NULL THEN NULL ELSE ST_GeomFromText(%(geom_wkt)s,25832) END,NOW())
    ON CONFLICT (source_system,source_id,signal_type) DO UPDATE SET
      title=EXCLUDED.title,publication_date=COALESCE(EXCLUDED.publication_date,iris_staging.signal_ingest.publication_date),
      source_url=EXCLUDED.source_url,municipality=EXCLUDED.municipality,state=EXCLUDED.state,
      geo_status=EXCLUDED.geo_status,quality_flags=EXCLUDED.quality_flags,
      geom=COALESCE(EXCLUDED.geom,iris_staging.signal_ingest.geom),observed_at=NOW()'''
    with conn.transaction():
        with conn.cursor() as cur:
            for record in records:
                cur.execute(sql, record)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixture', type=Path, help='Use saved HTML; default offline')
    ap.add_argument('--live', action='store_true', help='Opt-in public site retrieval')
    ap.add_argument('--load', action='store_true', help='Load into PostgreSQL using DATABASE_URL')
    ap.add_argument('--output', type=Path, default=Path('output.json'))
    args = ap.parse_args()
    if not args.fixture and not args.live:
        ap.error('Specify --fixture or --live')
    html = args.fixture.read_text(encoding='utf-8') if args.fixture else fetch_html(BASE)
    records = parse_html(html)
    args.output.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.load:
        import psycopg
        dsn = os.environ.get('DATABASE_URL')
        if not dsn:
            ap.error('DATABASE_URL required for --load')
        with psycopg.connect(dsn) as conn:
            ingest(conn, records)
    print(f'Parsed {len(records)} candidate records; output={args.output}')

if __name__ == '__main__':
    main()
