SELECT signal_type, geo_status, COUNT(*) AS n FROM iris_staging.signal_ingest GROUP BY 1,2 ORDER BY 1,2;
SELECT source_system, source_id, signal_type, COUNT(*) FROM iris_staging.signal_ingest GROUP BY 1,2,3 HAVING COUNT(*) > 1;
SELECT COUNT(*) AS missing_dates FROM iris_staging.signal_ingest WHERE publication_date IS NULL;
SELECT COUNT(*) AS unresolved_geographies FROM iris_staging.signal_ingest WHERE geom IS NULL;
SELECT DISTINCT ST_SRID(geom) AS srid FROM iris_staging.signal_ingest WHERE geom IS NOT NULL;
SELECT source_id, title, quality_flags FROM iris_staging.signal_ingest WHERE cardinality(quality_flags)>0;
