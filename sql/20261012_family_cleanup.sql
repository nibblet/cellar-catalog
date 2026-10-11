-- Family hygiene, 2026-10-12 (owner-approved plan). Re-files and one exact-proof merge; no maker fact changes.
-- 1. One Bluegrass Distillers brand, not two.
update cellar.products set brand = 'Bluegrass Distillers', brand_family = 'Bluegrass Distillers'
 where id = 'e92616a8-513d-4bb1-a64d-de1cdabccb8e' and facts_verified_at is null;
-- 2. 'Kentucky Peerless' rows belong to the Peerless family (no merges: name pairs here are only similar, review separately).
update cellar.products set brand = 'Peerless', brand_family = 'Peerless'
 where brand_family = 'Kentucky Peerless' and type = 'bourbon' and merged_into is null and facts_verified_at is null;
-- 3. Distiller's Share 03 exists twice with the same 112 proof (one carries the finish in its name): fold the bare one in.
select cellar.merge_product('2d262004-2937-4eda-942d-852146966b30', '5f0f36ef-4f83-4868-adc7-7d1446c6cfeb', null);
-- 4. A producer typo on a seed row (Jepthra -> Jeptha) and its maker link.
update cellar.products set producer = 'Jeptha Creed', producer_id = '8d2be687-ba2c-4690-be8a-9164aea03414'
 where id = '5fc7dc25-a836-4e3f-acd1-97ddd612e220' and facts_verified_at is null;
-- 5. Brand families split by name parsing (the same brand under a fragment and its full name): re-file into one.
update cellar.products p set brand = v.canon, brand_family = v.canon
from (values ('Bardstown','Bardstown Bourbon Company'), ('Big Bottom','Big Bottom Whiskey'), ('Burnside Goose Hollow','Burnside'),
             ('Devil''s River','Devils River'), ('Fathertime Bourbon','Fathertime'), ('Gold Bar','Gold Bar Whiskey'),
             ('Goodwood Brewing and','Goodwood'), ('Hancock''s Reserve','Hancock''s'), ('Pursuit','Pursuit United'),
             ('Red Line Whiskey Co.','Red Line'), ('Shady Mile High','Shady Mile'), ('Traverse City','Traverse City Whiskey Co.'),
             ('Watch Hill','Watch Hill Proper'), ('Wigle','Wigle Whiskey')) as v(fragment, canon)
where p.type = 'bourbon' and p.merged_into is null and p.brand_family = v.fragment and p.facts_verified_at is null;
-- 6. Two exact-proof duplicates with one name nested in the other.
select cellar.merge_product('ed7d1a4e-7667-471c-a1bb-899b7904b7a3', '1b68b52d-2afc-425b-b77b-bdde38571f41', null);  -- Elijah Craig Toasted Barrel Finish -> Toasted Barrel (94, maker)
select cellar.merge_product('69b5371b-759f-4544-a9a2-961b2a199a97', '50955216-efa5-4fb8-941f-bd5451f69f5a', null);  -- Hinterhaus Single Malt Discovery -> American Single Malt Discovery (92)
