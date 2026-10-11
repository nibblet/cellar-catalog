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
-- 7. Owner-directed merges (2026-10-12): Peerless comes in two lines, small batch and single barrel.
select cellar.merge_product('eb829e10-fcd9-4e9e-aaf8-797cb20169c6', '9b40b21e-f453-451f-a85e-e2ec9050ab28', null);  -- Peerless Rye -> Small Batch Rye (111.1)
select cellar.merge_product('ea4c6f68-06f2-4d78-af01-b539259b25c5', 'af105ecb-2432-42b6-9a37-9aaafd538870', null);  -- Peerless Bourbon -> Single Barrel Bourbon (114.0)
select cellar.merge_product('b7769fcf-71bd-4f5a-95b4-da31c8e11791', 'd9bc64a1-1f83-4f62-b52d-3135114ef435', null);  -- Peerless High Rye 110.6 -> High Rye 110.5 (same name)
-- Heaven's Door: Decade Series is the 10 year Tennessee bourbon at 100 proof, listed three ways; Cask Strength is the single barrel.
select cellar.merge_product('64da008e-ac5e-41a9-8410-8b1c756ff602', 'd02be228-4b00-41b7-b614-b1131eafb132', null);  -- Cask Strength -> Cask Strength, Single Barrel (121.8)
select cellar.merge_product('7f472e94-8296-4382-9996-121c47c05a73', '7b02d78c-1c17-4fe5-9a18-03539a4f3f55', null);  -- Tennessee Bourbon 10 Year -> Decade Series
select cellar.merge_product('714cf775-d03e-4640-99c2-871aa6d54658', '7b02d78c-1c17-4fe5-9a18-03539a4f3f55', null);  -- bare 'Heaven's Door' (10 yr, 100) -> Decade Series
