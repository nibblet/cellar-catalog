-- Owner decisions on the single-row sourced brands (third batch), 2026-10-13.
-- Burks Spring stays confirmed from the maker's launch release (no change).
-- The Morning Glory: the 109-proof seeds (the Office Cigar Lounge barrel pick and its hidden duplicate) fold into the maker's
-- 100-proof Bottled-in-Bond row; the pick's member save moves with it.
select cellar.merge_product('69ed94e1-37d4-4c22-9762-ff86610f9f22'::uuid, '7d95d836-d08e-4f44-b1ef-b5621fe893ad'::uuid, 'Office Cigar Lounge Barrel Pick');
select cellar.merge_product('4f164ee9-a621-4aea-907d-f0c64cf2b425'::uuid, '7d95d836-d08e-4f44-b1ef-b5621fe893ad'::uuid, null);  -- was merged into the pick; repoint to the parent
-- Ages to NAS: the maker states none (Morning Glory 4.5 yr died with the seeds; the parent is NAS; Distiller's Cache Rare Find 12 yr).
update cellar.products set age_years = null, age_label = 'NAS', nas = true where id in ('7d95d836-d08e-4f44-b1ef-b5621fe893ad', '744bdcc2-8429-4551-bc3a-f45dae239807');
-- One Distiller's Cache family: the Ugly Dog-filed row (94 proof, hidden seed) moves in; Ugly Dog owns the brand.
update cellar.products set brand = 'Distiller''s Cache', brand_family = 'Distiller''s Cache', name = 'Distiller''s Cache', expression = null,
  aliases = (select array_agg(distinct a) from unnest(array_append(aliases, 'Ugly Dog Distiller''s Cache')) a)
where id = 'f6050f04-2463-46c3-8c2f-edd0a3823242';
-- Burks Spring is distilled at Kentucky Artisan Distillery (the seed's specs said Maker's Mark).
update cellar.products set producer = 'Kentucky Artisan Distillery' where id = '17852f98-0fb9-4ac2-b14e-5fc4cef56e08';
