-- Drop hotlinked product artwork; keep only images we host ourselves.
--
-- 2,734 of 3,754 product images pointed straight at someone else's server — cigar makers
-- (drewestate.com, padron.com, arturofuente.com, myfathercigars.com, davidoffgeneva.com,
-- rockypatel.com, tatuajecigars.com …), distillers (buffalotracedistillery.com, michters.com,
-- makersmark.com …) and a retailer CDN. Two problems with that, independent of each other:
--
--   1. Rights. We do not hold a licence to display those images in a commercial app, and
--      answering Apple's Content Rights question honestly means not shipping them.
--   2. Delivery. We do not control those URLs. A site reorganisation, a referer block or a
--      swapped file breaks artwork in the shipped app with no change on our side.
--
-- The 1,020 images in our own Supabase storage bucket are kept: we control delivery, and that
-- smaller set can be audited for provenance separately (some were taken from review sites and
-- should still go — see out/image_url_backup_20260926.csv, rows marked third-party are the ones
-- this migration clears; the self-hosted rows are the ones that still need eyes on them).
--
-- The app shows a monogram wherever image_url is null, so clearing these degrades gracefully.
--
-- Reversible: every previous value is preserved below and in the CSV backup noted above.

begin;

-- Keep the old values in-database as well as in the CSV, so this can be undone without the file.
create table if not exists cellar.product_image_backup_20260926 as
select id, image_url, now() as backed_up_at
from cellar.products
where image_url is not null;

-- Clear anything not served from our own Supabase storage.
update cellar.products
set image_url = null
where image_url is not null
  and image_url not like '%jafcwggqgqxrcbuxjreo.supabase.co%';

commit;

-- Expected after running:
--   select count(*) from cellar.products where image_url is not null;  -- 1020
--   select count(*) from cellar.product_image_backup_20260926;         -- 3754
--
-- To undo:
--   update cellar.products p set image_url = b.image_url
--   from cellar.product_image_backup_20260926 b where b.id = p.id;
