CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS iris_staging;
CREATE TABLE IF NOT EXISTS iris_staging.signal_ingest (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_system TEXT NOT NULL,
 source_id TEXT NOT NULL,
 signal_type TEXT NOT NULL CHECK (signal_type IN ('solar_park','hyperscale_dc_inquiry')),
 title TEXT NOT NULL,
 publication_date DATE,
 source_url TEXT NOT NULL,
 municipality TEXT,
 state TEXT,
 geo_status TEXT NOT NULL,
 quality_flags TEXT[] NOT NULL DEFAULT '{}',
 geom geometry(Point,25832),
 observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(source_system,source_id,signal_type)
);
CREATE INDEX IF NOT EXISTS signal_ingest_geom_gix ON iris_staging.signal_ingest USING GIST(geom);
