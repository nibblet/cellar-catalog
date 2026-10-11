-- The 24 bourbon wheels with every one of the 39 leaves scored (the strict-schema bug in wheel-enrich.ts) were backed up in
-- 20261013_dense_wheels_backup.sql and cleared here so the fixed extractor rebuilds them from review text (2026-10-13).
update cellar.products set wheel_vector = null, trait_vector = null, wheel_version = null
where type = 'bourbon' and wheel_vector is not null and (select count(*) from jsonb_object_keys(wheel_vector)) >= 30;
