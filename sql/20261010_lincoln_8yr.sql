-- Bottle-in-hand add (owner label photo): Lincoln 8 Year Single Barrel, 105 proof / 52.5% ABV.
-- Maker, description and tasting notes from https://www.boundaryoak.co/lincoln, which lists no 8-year bottling.
-- source = 'manual' on purpose: the maker's page does not state this bottling's proof or age.
with m as (
  insert into cellar.makers (slug, name, type, country, website)
  values ('boundary-oak-distillery', 'Boundary Oak Distillery', 'bourbon', 'US', 'https://www.boundaryoak.co')
  on conflict (slug) do update set website = excluded.website
  returning id
)
insert into cellar.products (type, status, source, name, brand, brand_family, expression, producer, producer_id, proof, age_years, age_label, nas,
  expression_type, mash_style, spirit_type, bottled_in_bond, barrel_proof, is_core_range, catalog_included, aliases, source_url, source_checked_at, specs)
select 'bourbon', 'confirmed', 'manual', 'Lincoln 8 Year Single Barrel', 'Lincoln', 'Lincoln', '8 Year Single Barrel', 'Boundary Oak Distillery', m.id,
  105, 8, '8 yr', false, 'single_barrel', 'unknown', 'bourbon', false, false, false, true,
  array['Lincoln 8 Year', 'Lincoln Aged 8 Years Single Barrel'], 'https://www.boundaryoak.co/lincoln', now(),
  jsonb_build_object('proof', 105, 'abv', 52.5, 'age_years', 8, 'age_label', '8 yr', 'volume_ml', 750,
    'distillery', 'Boundary Oak Distillery, 2000 Boundary Oak Dr, Radcliff, KY 40160', 'class', 'Straight Bourbon Whiskey',
    'single_barrel', true, 'hand_signed', true,
    'tasting_notes_raw', 'Notes of sweet corn and honeyed grains, complemented by light hints of robust spices, such as cinnamon and nutmeg.',
    'description', 'Named for the Boundary Oak tree that stood for nearly 200 years on Sinking Spring Farm, where Abraham Lincoln was born.',
    'provenance', 'Proof, age, ABV and single-barrel status read from the bottle label (owner photo, 2026-10-10); maker, description and tasting notes from the distillery Lincoln page, which lists only a 105-120 proof / 2-4 year range for the line and no 8-year bottling.')
from m;
