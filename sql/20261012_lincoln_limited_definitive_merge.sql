-- Owner decision 2026-10-12: the Lincoln Cask Strength bottling is not on Boundary Oak's page, so it stays a second line, marked limited.
update cellar.products set rarity = 'limited'::cellar.rarity where id = '24f2896f-d229-4383-8e14-537563afb394' and facts_verified_at is null;
-- Family hygiene: the seeded "Definitive Series Batch 11" (115 proof, 12 yr, source ai, no producer) is the Watch Hill Definitive Series
-- row the importer added; its one member save moves to the parent.
select cellar.merge_product('5d2f2e2c-16f9-4d4c-b844-b7e65e2b7322'::uuid, '4cac8389-50b8-4315-a9b2-45518404aa22'::uuid, 'Batch 11');
