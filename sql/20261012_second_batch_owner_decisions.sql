-- Owner decisions on the second demand-ranked batch, 2026-10-12. Lincoln rows stay separate (no change).
-- Seeded ages the maker never states -> NAS: Backbone The Forge, Decade Down, Uncut Single Barrel; Pursuit Triple Batch Bourbon 108
-- (seeded "Blended Straight"); Journeyman Featherbone; all five Brother's Bond rows ("aged a minimum of N years" is not read).
update cellar.products set age_years = null, age_label = 'NAS', nas = true
where id in (
  '3c0d5c68-9ba4-43ee-97ea-f44bb8b12911', 'fc137c02-d4fa-4437-ba60-6adc414a4b63', '04a490f0-155a-475e-8ab8-aa239af55aab',
  'ea345976-9adf-473c-bf9b-b7e11dde1e8d', '105ec17c-e758-442c-b48c-59b31c000401',
  'e5bc6e42-7eaa-4fff-ad64-5076d665b9ea', '74270fd4-5302-4014-b25e-a3ff986952cc', 'efe15abb-4b2e-407f-b1d3-3c6a40b1bd4c',
  'ab6f0601-72cd-4ecb-b8cc-0cfb233ac5de', '9a95a82a-fb5f-4519-acd0-3196007d1b3b');
-- Calumet Farm 10 Year (owner-verified): the maker prints 74% corn / 18% rye / 8% malted barley, which is traditional, not wheated.
-- cellar.protect_verified_facts() blocks a change to a verified row unless facts_verified_at moves too, so it is re-stamped
-- (what the in-app editor does); facts_verified_by is left as is.
update cellar.products set mash_style = 'traditional', facts_verified_at = now() where id = '99370cba-178d-435c-a8d0-997cf164f2ec';
