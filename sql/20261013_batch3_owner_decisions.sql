-- Owner decisions on the third demand-ranked batch (Henry McKenna / On Your Six / Trackside), 2026-10-13.
-- Henry McKenna: the seeded 80-proof flagship (bottled_in_bond = true, impossible at 80) is folded into the verified Single Barrel
-- Bottled-in-Bond row (no member saves on the child).
select cellar.merge_product('943a52a9-34e6-4014-9530-8278253055c7'::uuid, '456f5ae0-f62b-41f8-9052-16c1ad0b4bfc'::uuid, null);
-- The verified row now reads as maker-sourced: heavenhilldistillery.com/henry-mckenna-single-barrel.php states 100 proof, 10 years, Bottled-in-Bond.
-- Only source/status/source_url move, so facts_verified_at stays (the trigger guards fact columns only).
update cellar.products set source = 'maker', status = 'confirmed', source_url = 'https://www.heavenhilldistillery.com/henry-mckenna-single-barrel.php', source_checked_at = now() where id = '456f5ae0-f62b-41f8-9052-16c1ad0b4bfc';
-- On Your Six: the maker's page states the recipe.
update cellar.products set mash_bill = '72% Corn, 18% Rye, 10% Barley' where id = '801c6450-fce8-4afe-958f-fc73a4d7e8d8';
