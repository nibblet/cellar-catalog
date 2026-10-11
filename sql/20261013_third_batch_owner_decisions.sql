-- Owner decisions on the third batch, round two, 2026-10-13.
-- 1. Clear all seeded ages the maker never states or states only as a floor (Triple Peat's 4.17 and every age a page states stay).
update cellar.products set age_years = null, age_label = 'NAS', nas = true
where facts_verified_at is null and merged_into is null and id in (
  -- Chattanooga: 91, 111 Cask, 99 Rye, Founder's 10th (garbled label) / 12th / 13th / 14th, finishing casks, Centenary
  '10b8c4c4-a644-4336-8c11-7663fa823de4', '5ad7172e-f6e4-46bb-8f5f-19aa7ca65bab', '8729c697-fd43-42ba-b4b4-fd7ab54c2431',
  'e02e2970-260b-4e44-8364-091f0acfa71d', '60421556-b4a3-4654-8397-6d596c958255', 'd8ee7af8-6554-48f0-9ddc-12e9e0463004',
  'b5dfa7ab-0690-42c9-a61c-d888a05e1645', '88456273-e7e0-42b3-b207-376071b6c32b', '16a6b265-37a9-465b-add5-2cfddad7e127',
  '4145aad0-c9cd-4122-93c8-63fc50cd34a6', '58846e34-2c95-4706-81d8-5ff2bbcfa70f', 'b525a2cd-9d52-4857-a485-014ab074d607',
  '8238c137-bf88-4e28-b8bf-f0a597cb099e', '84d4ebf6-d097-45cd-9b6f-ab5f904fbe0b', '976ccd69-d402-4baf-872a-f6a819315b5b',
  'ca1ba0fc-a9f1-4d2c-b25b-54e6dd72744b',
  -- Frey Ranch: Farm Strength Uncut, Single Grain Barley, and the off-site seeds (Malted Corn, Smoked, Quad Malt, Five Grain)
  '55c8d851-ff88-44b6-9adf-d587216d1ba5', '2e259a05-15e9-4a9d-aea9-b2f88ee5643e', 'b0ff85a3-910b-4726-b72f-8388a8f8993f',
  '70de2995-1dfd-491b-a104-b6938141cc03', 'a3dbeb5c-55e7-4788-a334-6876ebe93651', 'c2017dd3-e0ca-40a2-a578-6ec5c9c561cc',
  -- Milam & Greene: Port Rye, Unabridged (junk label), the off-site flagship and Castle Hill
  'b80d8066-f009-48a1-acdb-93bf59a39a99', '50d2a031-2a05-435e-8001-7afdddeee14e', '122fa936-945a-442f-822d-a32661cce2dd',
  '3e9dc244-b210-4b8d-b4a0-67df9343025b',
  -- Still Austin: Musician, Artist Rye, Cask Strength, Cask Strength Rye, the four Bottled in Bond rows
  '95f620b2-e269-4dc7-ab60-a4a45ef40c79', '40729f55-a2d1-46aa-8484-bbefe0178b6a', 'ae1f07c8-6531-4d96-874d-b7768587b701',
  '9a99f669-bf6f-496e-b980-3c31a6cc0dd2', 'b3fd2c49-0d92-4fd5-b1e2-d3f994954c06', '28e9cd8c-5b32-425c-a39f-403a20fad02d',
  '31e8b2f7-998f-48ea-9d05-b478d9833921', '4b6c6e04-2216-4743-8937-126d466f6c67',
  -- Copperworks: Color Cask, Kilt Lifter, Pondera, Red Wine, Amaro, Port Cask Finish, Single Cask No. 440
  '26a0516f-6c80-444f-b9d9-4250c1c7e4db', 'b827f2bb-0422-44c0-9731-14cdbfd3e0c6', '16e81769-d735-4659-9a6e-a26a9e8c9cb9',
  'b4de96b9-a07a-405e-81ed-c159d006a770', '35e6eff4-005a-49a3-9d96-d1b069d81a9b', 'f2cf6904-a556-4bbf-8dea-75fec1d8189e',
  'aa482615-5464-4164-81df-d3ff0404ed10',
  -- Three Chord: Hard Pressed, Strange Collaboration (also merged below), Twelve Bar Reserve, Whiskey Drummer
  'a47053cd-74d5-4107-ab68-96668b0673fb', 'ffe88d75-f64e-45e3-8c52-4300c7dc70a1', '2fdb7bd9-5ef7-4948-87d9-39ad11ef31a0',
  '0d35fc3b-3105-4744-9622-75937d1a5c1d',
  -- the refiled Distiller's Cache row
  'f6050f04-2463-46c3-8c2f-edd0a3823242');
-- 2. Frey Farm Strength Uncut Bourbon stays as it is (core, browsable): no change.
-- 3. Three Chord: the seeded "Strange Collaboration" folds into the maker's "Strange Collab" at 99 proof (owner's reading). The maker's
--    page states 86, so the row is stamped owner-verified to keep an importer from reverting it (importers skip verified rows).
select cellar.merge_product('ffe88d75-f64e-45e3-8c52-4300c7dc70a1'::uuid, '02fd2a2a-81b9-4cc1-9fd9-a8aeeaca8980'::uuid, null);
update cellar.products set proof = 99, facts_verified_at = now() where id = '02fd2a2a-81b9-4cc1-9fd9-a8aeeaca8980';
