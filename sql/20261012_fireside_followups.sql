-- Fireside follow-ups, 2026-10-12 (owner asked to merge Fireside; the importer proved the 105.6-proof rows are distinct bottlings).
-- The earlier Hazmat barrels fold into the program row, keeping their release labels.
select cellar.merge_product('42bb982b-cf4f-44e6-a2a9-eb1b1054cd55', 'a75ef8b6-f6b5-4eee-b559-68654370a8e8', '6 Year 141.2 Proof');
select cellar.merge_product('8709497f-41c4-425d-927b-6c7820032d19', 'a75ef8b6-f6b5-4eee-b559-68654370a8e8', '7 Year 142 Proof');
-- The stray 'Fireside High' family is the High Rye bourbon.
update cellar.products set brand = 'Fireside', brand_family = 'Fireside', expression = 'High Rye' where id = '1eb05738-5a35-43c5-b0a0-a4b05a5e5a40' and facts_verified_at is null;
update cellar.products set producer = 'Mile High Spirits' where brand_family = 'Fireside' and producer = 'Mile High Spirit' and facts_verified_at is null;
