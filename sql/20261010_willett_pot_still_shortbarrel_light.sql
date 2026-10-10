-- Two bottle-in-hand adds from the owner's cellar (source='manual'): only the
-- proof printed on the label is asserted; everything else stays null/unknown.
insert into cellar.products (type, status, source, name, brand, brand_family, expression, producer, producer_id, proof, nas,
  expression_type, mash_style, spirit_type, bottled_in_bond, barrel_proof, is_core_range, catalog_included, aliases, source_checked_at, specs)
select 'bourbon','confirmed','manual','Willett Pot Still Reserve Cask Strength','Willett','Willett','Pot Still Reserve Cask Strength','Willett', m.id,
  120, true, 'limited','unknown','bourbon', false, true, false, true,
  array['Willett Pot Still Cask Strength','Willett Pot Still Reserve 120 Proof'], now(),
  jsonb_build_object('proof', 120, 'abv', 60.0, 'cask_strength', true, 'note', 'Bottle in hand; not the standard 94-proof Pot Still Reserve')
from cellar.makers m where m.slug = 'willett';

insert into cellar.products (type, status, source, name, brand, brand_family, expression, producer, producer_id, proof, nas,
  expression_type, mash_style, spirit_type, bottled_in_bond, barrel_proof, is_core_range, catalog_included, aliases, source_checked_at, specs)
select 'bourbon','confirmed','manual','Shortbarrel Light Whiskey','Shortbarrel','Shortbarrel','Light Whiskey','Shortbarrel', m.id,
  144.4, true, 'standard','unknown','other', false, false, false, true,
  array['Shortbarrel American Light Whiskey','Short Barrel Light Whiskey'], now(),
  jsonb_build_object('proof', 144.4, 'abv', 72.2, 'class', 'light whiskey', 'note', 'Bottle in hand')
from cellar.makers m where m.slug = 'shortbarrel';
