-- Bourbon Phase 0: the last hand-fix before the maker importers (BOURBON.md) take over.
-- Applied to project jafcwggqgqxrcbuxjreo on 2026-09-21 via the Supabase MCP, section by section.
--
-- What it does, in order:
--   A. fold duplicates that straddled the catalog_included line (cellar.merge_product carries saves,
--      tastings, reviews, images; we add source_url + aliases by hand)
--   B. rename the survivors to the bar-order name; correct stale facts
--   C. promote the flagships: every standard expression of a Tier-1 producer becomes browsable
--   D. rarity on every included row that had none
--   E. is_core_range: anniversaries, experiments and one-offs are not core
-- Nothing is deleted; nothing verified is touched; no row is stamped facts_verified_at (the
-- importers must still be allowed to overwrite these from the maker's page).

------------------------------------------------------------------------------------------------
-- A. Merges: child -> parent (release the bottle inherits)
------------------------------------------------------------------------------------------------
select cellar.merge_product('fd114266-7573-4447-97b5-df257989b04e', '57dd54ad-63c9-4991-adee-c65f7b1ebbfd', null); -- Eagle Rare -> Eagle Rare 10 Year Single Barrel
select cellar.merge_product('94a29c4e-fbef-4df2-9462-416ef7deeeab', 'a8fce06d-8263-45e1-b4c7-920809ea9648', null); -- Woodford Reserve -> Distiller's Select
select cellar.merge_product('d418acd1-7540-46f3-8fd8-f06ee5ad5ace', 'e811d4b9-7635-43fc-afb9-e66f1f9efd92', null); -- W.L. Weller 12 Year -> Weller 12 Year
select cellar.merge_product('0b3ad455-27ba-4185-867e-10fcaedb9397', '8b5cc01d-b4c4-4b11-ae16-6dd3059cd8ca', null); -- W.L. Weller Antique 107 -> Weller Antique 107
select cellar.merge_product('a148f3cf-d705-4426-ae40-d09df2922adf', '9c24e0ec-bc65-4ad6-a35f-727af74286cf', null); -- Maker's 46 Straight Bourbon -> Maker's Mark No. 46 French Oaked
select cellar.merge_product('84ae7ba8-6496-4ee8-9eee-6985753c1ea6', '3db80b59-7419-4f48-915a-91ede8f0694a', null); -- Elijah Craig Small Batch -> Elijah Craig (enriched row survives)
select cellar.merge_product('4dd29419-5049-4a16-8f66-6e80afad43fe', '3db80b59-7419-4f48-915a-91ede8f0694a', '12 Year'); -- Elijah Craig 12 Year (pre-2016) -> Elijah Craig
select cellar.merge_product('d2b44867-7027-476c-99ed-4046c30e6849', 'd0cb6594-54ee-4b3a-bb32-7646cab264c2', '2023-03 ''Mighty Fine Batch'''); -- batch row -> Booker's Bourbon
select cellar.merge_product('194e625e-d0fb-436a-b9a4-656bc606703a', '86527c04-7e1c-4dda-b497-6e35fa8bd7ca', null); -- Old No 7 -> Jack Daniel's
select cellar.merge_product('2376295b-1775-4ee9-902b-24fdeacb3a05', '76a77e91-67b1-4bb8-b4d1-1c8604154974', null); -- Benchmark Old No. 8 Brand (draft) -> Benchmark (enriched)
select cellar.merge_product('b8410e9b-5cf2-4a47-ae2b-bac2192e34f4', '2ee0be75-2daf-4c20-aa25-aa95b21f515b', null); -- Old Ezra 7 Year -> Old Ezra
select cellar.merge_product('6f2c6b99-1b3c-4c04-b67c-3280240407fa', '8404a9ba-862b-42f3-9d1f-62dce801e2f2', null); -- Old Ezra 7 Year Barrel Strength -> Old Ezra Barrel Strength
select cellar.merge_product('b7f54a88-69c9-4c19-9f7b-e31e497e580a', '96bbc853-4307-45c5-8360-6f49195bc72d', null); -- 1792 Ridgemont Reserve (old name) -> 1792 Small Batch
select cellar.merge_product('56a021a2-18b3-4ccb-8b19-22bd92480bf7', 'd7d56921-0225-4ce9-b9a1-7b4f0589b4a6', null); -- Coopers Craft Straight Bourbon -> Coopers Craft
select cellar.merge_product('48ef2571-d9a7-4ab9-8c53-84072ebdda52', '7b7b9523-6aec-4c3f-a8c9-e92780f7728c', null); -- Heaven Hill 7 Year BiB -> Heaven Hill Bottled in Bond
select cellar.merge_product('7d6af9e5-2852-4f4f-85bf-3fcdaa98b45d', '7492d321-d674-40cb-a589-2cd9f43ba81e', null); -- EHT Bottled-In-Bond Bourbon (= Small Batch) -> EHT Small Batch
select cellar.merge_product('4653a9a9-731c-4614-aa63-d5e014cf973f', 'b8ff01f3-78f0-44cd-a0f2-0f4c884cec72', null); -- Belle Meade (BB draft) -> Belle Meade (enriched, filed under Nelson's Green Brier)
select cellar.merge_product('3d4b29ce-853d-41ae-8912-82c8bac43544', 'b8ff01f3-78f0-44cd-a0f2-0f4c884cec72', null); -- Belle Meade Sour Mash (same bottle) -> Belle Meade

-- The merge helper carries images and verified facts; carry the child's provenance and name too.
with kids as (
  select c.merged_into as pid, min(c.source_url) as url, array_agg(distinct x) filter (where x is not null) as al
  from cellar.products c cross join lateral unnest(c.aliases || array[c.name]) as x
  where c.type = 'bourbon' and c.merged_into is not null and c.updated_at > now() - interval '1 hour'
  group by c.merged_into)
update cellar.products p set
  source_url = coalesce(p.source_url, k.url),
  aliases = (select coalesce(array_agg(distinct a), '{}'::text[]) from unnest(p.aliases || k.al) as a where a <> p.name)
from kids k where k.pid = p.id;

------------------------------------------------------------------------------------------------
-- B. Survivors take the bar-order name; stale facts corrected
------------------------------------------------------------------------------------------------
update cellar.products set name = 'Eagle Rare 10 Year', expression = '10 Year', aliases = aliases || array['Eagle Rare 10 Year Single Barrel','Eagle Rare 10'] where id = '57dd54ad-63c9-4991-adee-c65f7b1ebbfd';
update cellar.products set name = 'Maker''s Mark 46', expression = '46', age_years = null, age_label = 'NAS', nas = true, msrp_usd = coalesce(msrp_usd, 40), aliases = aliases || array['Maker''s 46','Maker''s Mark No. 46 French Oaked'] where id = '9c24e0ec-bc65-4ad6-a35f-727af74286cf';
update cellar.products set name = 'Elijah Craig Small Batch', expression = 'Small Batch', age_years = null, age_label = 'NAS', nas = true, expression_type = 'small_batch', rarity = 'shelf', msrp_usd = 30, aliases = aliases || array['Elijah Craig','EC Small Batch','ECSB'] where id = '3db80b59-7419-4f48-915a-91ede8f0694a';
update cellar.products set name = 'Booker''s', expression = null, age_years = null, age_label = '6–8 yr', nas = false, rarity = 'limited', is_core_range = true, msrp_usd = 90, release_pattern = 'batch', aliases = aliases || array['Booker''s Bourbon','Booker''s Small Batch'] where id = 'd0cb6594-54ee-4b3a-bb32-7646cab264c2';
update cellar.products set name = 'Jack Daniel''s Old No. 7', expression = 'Old No. 7', age_years = null, age_label = 'NAS', nas = true, rarity = 'shelf', is_core_range = true, aliases = aliases || array['Jack Daniel''s','Jack Daniel''s Tennessee Whiskey','JD','Old No. 7','Old No 7'] where id = '86527c04-7e1c-4dda-b497-6e35fa8bd7ca';
update cellar.products set name = 'Benchmark Old No. 8', expression = 'Old No. 8', proof = 80, age_years = null, age_label = 'NAS', nas = true, rarity = 'shelf', is_core_range = true, msrp_usd = coalesce(msrp_usd, 15), aliases = aliases || array['Benchmark','Benchmark Old No. 8 Brand','Benchmark Bourbon'] where id = '76a77e91-67b1-4bb8-b4d1-1c8604154974';
update cellar.products set name = 'Coopers'' Craft', expression = null, age_years = null, age_label = 'NAS', nas = true, rarity = 'shelf', is_core_range = true, aliases = aliases || array['Coopers Craft','Coopers'' Craft Bourbon'] where id = 'd7d56921-0225-4ce9-b9a1-7b4f0589b4a6';
update cellar.products set proof = 101, age_years = 7, age_label = '7 yr', nas = false, rarity = 'shelf' where id = '2ee0be75-2daf-4c20-aa25-aa95b21f515b'; -- Old Ezra
update cellar.products set proof = 117, age_years = 7, age_label = '7 yr', nas = false, barrel_proof = true, rarity = 'shelf' where id = '8404a9ba-862b-42f3-9d1f-62dce801e2f2'; -- Old Ezra Barrel Strength
update cellar.products set proof = 100, age_years = 7, age_label = '7 yr', nas = false, bottled_in_bond = true where id = '7b7b9523-6aec-4c3f-a8c9-e92780f7728c'; -- Heaven Hill BiB
update cellar.products set bottled_in_bond = true, aliases = aliases || array['EHT Small Batch','E.H. Taylor Small Batch'] where id = '7492d321-d674-40cb-a589-2cd9f43ba81e';
update cellar.products set age_years = null, age_label = 'NAS', nas = true where id = '8b5cc01d-b4c4-4b11-ae16-6dd3059cd8ca'; -- Weller Antique 107 dropped its age statement years ago
update cellar.products set aliases = aliases || array['Woodford Reserve','Woodford'] where id = 'a8fce06d-8263-45e1-b4c7-920809ea9648';
update cellar.products set aliases = aliases || array['W.L. Weller 12 Year','Weller 12'] where id = 'e811d4b9-7635-43fc-afb9-e66f1f9efd92';
update cellar.products set aliases = aliases || array['1792 Ridgemont Reserve','Ridgemont Reserve'] where id = '96bbc853-4307-45c5-8360-6f49195bc72d';
update cellar.products set brand_family = 'Belle Meade', expression = null, age_years = null, age_label = 'NAS', nas = true, aliases = aliases || array['Belle Meade Sour Mash','Belle Meade Bourbon'] where id = 'b8ff01f3-78f0-44cd-a0f2-0f4c884cec72';
update cellar.products set brand_family = 'Belle Meade' where id = '863510aa-242d-4af1-add7-b546b90c3eac'; -- Honey Cask stays a Belle Meade

-- Stale facts on rows that stay
update cellar.products set age_years = null, age_label = 'Varies by batch', nas = false where name = 'Elijah Craig Barrel Proof' and merged_into is null and facts_verified_at is null;
update cellar.products set age_years = null, age_label = 'NAS', nas = true where name = 'Henry McKenna' and merged_into is null and facts_verified_at is null; -- 80-proof Sour Mash is NAS; the 10 yr is the BiB single barrel
update cellar.products set age_years = 6, age_label = '6 yr', nas = false where id = 'd00a1447-60a9-48d5-97a9-9f5117010d3d'; -- Bib & Tucker Small Batch is the 6 Year; the 12 came from the 12 Year page
update cellar.products set age_years = null, age_label = 'NAS', nas = true where id = '21f8c655-a543-40b4-a603-46dd9f3a1403'; -- Blade and Bow (decisions.md #10)
update cellar.products set rarity = 'allocated', msrp_usd = 150 where name = 'Eagle Rare 12 Year' and merged_into is null and facts_verified_at is null;
update cellar.products set spirit_type = 'tennessee' where name = 'George Dickel Superior No. 12' and merged_into is null;
update cellar.products set name = 'George Dickel Bourbon', expression = 'Bourbon', aliases = aliases || array['George Dickel','George Dickel 8 Year Bourbon'] where id = '3b0819cd-ac76-404f-98fb-9222f86e0a4e';
update cellar.products set brand_family = 'George Dickel' where id = 'd69f231f-f35c-423b-9863-b9907fa9a883'; -- was filed under Cascade Hollow
update cellar.products set name = 'Bulleit 95 Rye', expression = '95 Rye', aliases = aliases || array['Bulleit Rye','Bulleit 95 Whiskey Rye'] where name = 'Bulleit 95 Whiskey Rye' and merged_into is null;
update cellar.products set name = 'Jim Beam Devil''s Cut', aliases = aliases || array['Devil''s Cut'] where name = 'Devil''s Cut' and brand_family = 'Jim Beam' and merged_into is null;
update cellar.products set aliases = aliases || array['Old Forester 86','Old Forester 86 Proof'] where name = 'Old Forester Classic Bourbon' and merged_into is null;
update cellar.products set brand_family = '2XO', rarity = 'limited' where id = '0e32fd0d-724e-406b-acd5-06f1034e5dfa';
update cellar.products set discontinued = true, catalog_included = false, rarity = 'limited', name = 'Wild Turkey 81', expression = '81', aliases = aliases || array['Wild Turkey'] where id = '6c459181-a90a-4dd1-81bd-b12fa8ebda14'; -- WT 81 was dropped in 2023

------------------------------------------------------------------------------------------------
-- C. Promote the flagships (name, rarity, core)
------------------------------------------------------------------------------------------------
with v(name, rarity, core) as (values
  ('Buffalo Trace', 'shelf', true),
  ('Booker''s', 'limited', true),
  ('Jack Daniel''s Old No. 7', 'shelf', true),
  ('Jack Daniel''s Gentleman Jack', 'shelf', true),
  ('Jack Daniel''s Tennessee Rye', 'shelf', true),
  ('Old Forester Single Barrel', 'shelf', true),
  ('Old Forester Classic Bourbon', 'shelf', true),
  ('Old Forester Rye', 'shelf', true),
  ('Woodford Reserve Distiller''s Select Rye', 'shelf', true),
  ('Elijah Craig Barrel Proof', 'allocated', true),
  ('Elijah Craig Rye', 'shelf', true),
  ('Bulleit Bourbon', 'shelf', true),
  ('Bulleit 95 Rye', 'shelf', true),
  ('Bulleit 10 Year', 'shelf', true),
  ('Bulleit Barrel Strength', 'limited', false),
  ('George Dickel Bourbon', 'shelf', true),
  ('George Dickel Superior No. 12', 'shelf', true),
  ('George Dickel Rye', 'shelf', true),
  ('George Dickel Bottled In Bond', 'limited', false),
  ('Henry McKenna', 'shelf', true),
  ('Jim Beam Devil''s Cut', 'shelf', true),
  ('Jim Beam Old Tub', 'shelf', true),
  ('Wild Turkey Rare Breed Rye', 'shelf', true),
  ('Ezra Brooks 99 Bourbon', 'shelf', true),
  ('Rebel', 'shelf', true),
  ('Rebel 100', 'shelf', true),
  ('Jefferson''s Reserve', 'shelf', true),
  ('Angel''s Envy Cask Strength', 'allocated', false),
  ('Elmer T. Lee', 'allocated', true),
  ('Hancock''s President''s Reserve Single Barrel', 'allocated', true),
  ('William Larue Weller', 'lottery', false),
  ('Sazerac 18 Year Rye', 'lottery', false),
  ('Thomas H. Handy Rye', 'lottery', false),
  ('Weller Single Barrel', 'allocated', true),
  ('Weller C.Y.P.B.', 'allocated', false),
  ('Colonel E.H. Taylor Rye', 'allocated', true),
  ('Michter''s US*1 Original Sour Mash', 'shelf', true),
  ('Michter''s US*1 Single Barrel Rye', 'shelf', true),
  ('Coopers'' Craft', 'shelf', true),
  ('Benchmark Old No. 8', 'shelf', true),
  ('Belle Meade', 'shelf', true),
  ('Smoke Wagon', 'shelf', true),
  ('Smoke Wagon Small Batch', 'shelf', true),
  ('Traveller', 'shelf', true),
  ('Bib & Tucker', 'shelf', true),
  ('Blade and Bow', 'shelf', true),
  ('Bernheim Original Wheat Whiskey', 'shelf', true),
  ('Legent', 'shelf', true),
  ('Old Rip Van Winkle 10 Year', 'lottery', false),
  ('Pappy Van Winkle 15 Year', 'lottery', false),
  ('Pappy Van Winkle 20 Year', 'lottery', false),
  ('Pappy Van Winkle 23 Year', 'unicorn', false)
)
update cellar.products p set catalog_included = true, is_core_range = v.core, status = 'confirmed',
  rarity = case when p.facts_verified_at is null then v.rarity::cellar.rarity else p.rarity end -- verified rows keep their facts (ECBP)
from v where p.type = 'bourbon' and p.merged_into is null and p.name = v.name;

------------------------------------------------------------------------------------------------
-- D. Rarity on included rows that had none
------------------------------------------------------------------------------------------------
with v(name, rarity) as (values
  ('Benchmark Bonded Bourbon','shelf'),('Benchmark Full Proof','shelf'),('Benchmark Single Barrel','shelf'),('Benchmark Small Batch','shelf'),('Benchmark Top Floor','shelf'),
  ('Blanton''s Gold Edition','allocated'),('Blanton''s Special Reserve','limited'),('Blanton''s Straight From the Barrel','allocated'),
  ('Early Times Bottled in Bond','shelf'),('Elijah Craig 18 Year Single Barrel','allocated'),
  ('Evan Williams 12 Year','limited'),('Evan Williams 1783 Small Batch','shelf'),('Evan Williams 23 Year','allocated'),('Evan Williams Black Label','shelf'),('Evan Williams Bottled in Bond','shelf'),('Evan Williams Master Blend','limited'),
  ('Ezra B 12 Year Single Barrel','shelf'),('Fighting Cock','shelf'),('Four Roses Super Premium','limited'),('Four Roses Yellow Label','shelf'),
  ('Heaven Hill Select Stock Cognac Finished','allocated'),('J.T.S. Brown Bottled in Bond','shelf'),
  ('Jim Beam Black XA Extra Aged','shelf'),('Jim Beam Double Oak','shelf'),('Jim Beam White Label','shelf'),('Kentucky Gentleman','shelf'),
  ('Knob Creek 10 Year Rye','limited'),('Knob Creek Rye','shelf'),('Mellow Corn','shelf'),('New Riff','shelf'),('Old Bardstown Estate Bottled','shelf'),
  ('Old Crow','shelf'),('Old Grand-Dad','shelf'),('Old Grand-Dad Bonded Bourbon','shelf'),('Orphan Barrel Fanged Pursuit','limited'),
  ('Peerless Small Batch Barrel Proof','shelf'),('Pikesville 6 Year Rye','shelf'),('Quality House Old Style','shelf'),('Rittenhouse Bottled in Bond Rye','shelf'),
  ('Rock Hill Farms Single Barrel','allocated'),('Rock Town Column Still Collection Small Batch','shelf'),('Rock Town Column Still Collection Toasted French Oak Barrel Finish','limited'),
  ('Russell''s Reserve 6 Year Rye','shelf'),('Russell''s Reserve Single Barrel Rye','shelf'),('Sazerac Rye','shelf'),
  ('Starlight Bottled in Bond','shelf'),('Starlight Bottled in Bond Rye','shelf'),('Starlight Carl T. Huber''s Bottled in Bond','shelf'),
  ('Starlight Carl T. Huber''s Bourbon Finished in Madeira Casks','limited'),('Starlight Carl T. Huber''s Single Barrel Bourbon Finished in Honey Barrels','limited'),
  ('Starlight Carl T. Huber''s Single Barrel Rye Finished in Honey Barrels','limited'),('Starlight Huber''s Rickhouse Select Single Barrel','limited'),
  ('Starlight Old Rickhouse Double Oaked Rye','limited'),('Starlight Old Rickhouse Rye','shelf'),('Starlight Old Rickhouse Rye Whiskey Finished in Sherry Barrels','limited'),
  ('Starlight Single Barrel Rye Finished in Triple Sec Barrels','limited'),('Ten High Sour Mash','shelf'),('The Mattie Gladden Bottled in Bond','shelf'),
  ('Town Branch 6 Year Wheated','shelf'),('Town Branch 7 Year Kentucky Single Malt','shelf'),('Town Branch True Cask','shelf'),
  ('Willett Family Estate Small Batch 4 Year','limited'),('Woodinville Finished in Port Casks','limited')
)
update cellar.products p set rarity = v.rarity::cellar.rarity
from v where p.type = 'bourbon' and p.merged_into is null and p.rarity is null and p.name = v.name;

------------------------------------------------------------------------------------------------
-- E. is_core_range: not core
------------------------------------------------------------------------------------------------
update cellar.products set is_core_range = false where type = 'bourbon' and merged_into is null and name in (
  'Four Roses 100th Anniversary','Four Roses 120th Anniversary','Four Roses 130th Anniversary','Four Roses Limited Edition','Four Roses Mariage Collection',
  'Wild Turkey ''Tradition''','Wild Turkey American Spirit','Wild Turkey Bond & Lillard','Wild Turkey Diamond Anniversary','Wild Turkey Forgiven',
  'Wild Turkey Generations','Wild Turkey Old Ripy','Wild Turkey Tribute','Wild Turkey W.B. Saffell Kentucky Straight',
  '15 Minute Infrared Light Wave Barrels','30 Minute Infrared Light Wave Barrels','Buffalo Trace Single Oak Project Rye Bourbon, Barrel #80',
  'Jack Daniel''s Single Barrel Barrel Proof Rye','Jack Daniel''s Single Barrel Heritage Barrel','George Dickel 15 Year Single Barrel','Bib & Tucker 12 Year Single Barrel Select',
  'RD One Smoked Oak & Maple Wood','Peerless Double Oak');

------------------------------------------------------------------------------------------------
-- F. A bottle a member has saved is always carried (the May cut-back rule, re-applied)
------------------------------------------------------------------------------------------------
select cellar.merge_product((select id from cellar.products where name='Fusion Series' and brand_family='Bardstown' and merged_into is null),
                            (select id from cellar.products where name='Bardstown Bourbon Company Fusion Series' and merged_into is null), null);
update cellar.products set brand_family = '2XO' where brand_family = 'Two Times Oak' and merged_into is null;
update cellar.products p set catalog_included = true
from cellar.member_saves s where s.product_id = p.id and p.type='bourbon' and p.merged_into is null and not p.catalog_included;

-- Result: 374 live rows (was 307), 19 merges, 0 included rows without rarity, 0 member saves pointing at hidden rows.
