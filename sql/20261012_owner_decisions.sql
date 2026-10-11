-- Owner decisions 2026-10-12 (items 1-5 of the end-of-round list). All guarded by facts_verified_at is null.
-- 1. Seeded ages the maker never states (or contradicts) -> NAS.
update cellar.products set age_years = null, age_label = 'NAS', nas = true
 where id in ('3d6b3440-bf4f-4e45-97f7-1adf5856e42b',  -- H.K. Young Toasted Barrel Blend (6; maker says "7 - 8")
              '849714fa-4d20-450a-933c-b560255727f4',  -- Horse Soldier (4; "small batches of 4 year old bourbon")
              '92321f6d-7d85-4244-8349-576bfcfa11e8',  -- Shortbarrel Four Grain (4; "four-to-five-year-old")
              '928145b6-5e70-40df-a4d1-245273e80589',  -- Town Branch (4; maker: non-age-stated)
              'd4b450ff-d2dc-4886-8c29-a1c6d9bef93c',  -- Hard Truth Sweet Mash Four Grain (5)
              'de80a73d-77b3-4df5-830b-8a6d2337cf1d',  -- Hard Truth Sweet Mash Wheated (5)
              'af294078-4d4f-4748-98d7-d702519c183e',  -- Blue Note Special Reserve (9.59; page says "4-19 Years")
              'e88d07d5-fe63-479b-9837-4242863cf420',  -- Blue Note Honey Bourbon Cask (3)
              'a6ffd571-4823-43ed-bd35-7592aa1b84a2')  -- Blue Note Honey Rye Cask (3)
   and facts_verified_at is null;
-- 2. The two MGP-sourced Eighteen33 rows are retired.
update cellar.products set discontinued = true
 where id in ('576cd7b5-7d53-4cc7-82f7-d29ec235e37a', 'bf7085ef-7eed-4ee5-a6a6-0c479c9f0301') and facts_verified_at is null;
-- 3. Town Branch Reserve Rye is Single Barrel Reserve Rye (both seed, 100 proof; the save carries over).
select cellar.merge_product('e1b606aa-fa57-4196-aaeb-19140871caed', '4aceeee0-6d09-4f7e-84cd-770ba1b37726', null);
-- 4. O.K.I. is OKI Spirits LLC (MGP is the sourced distillate, not the maker).
update cellar.makers set name = 'OKI Spirits LLC' where id = '927e2231-8384-4f4b-b5bc-8ad8f9282fc2';
update cellar.products set producer = 'OKI Spirits LLC', producer_id = '927e2231-8384-4f4b-b5bc-8ad8f9282fc2'
 where id in ('f27a8549-680c-4566-9c08-71000e479957', 'a510df2c-419d-4884-acdd-1c148a583729',
              '5792dbf5-3a2c-4185-ab18-cbc4b80ef8f0', 'ac0ff254-f5e0-4c3c-bec3-ee731ca76441') and facts_verified_at is null;
-- 5. Fireside Single Barrel (4 yr) is not on the maker's site: no longer core.
update cellar.products set is_core_range = false where id = 'c4b64720-a4f7-4460-9cf0-d7205d7465ca' and facts_verified_at is null;
