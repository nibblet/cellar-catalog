-- Applied to Supabase as migrations "catalog_scorecard" and "catalog_scorecard_wrapper_or_origin"
-- on 2026-09-20 (the second re-created the view with wrapper-or-origin completeness). Kept as the record.
alter table cellar.products add column if not exists source_checked_at timestamptz;
update cellar.products set source_checked_at = updated_at where source = 'maker' and source_checked_at is null;

drop view if exists cellar.catalog_scorecard;
create view cellar.catalog_scorecard as
with live as (
  select * from cellar.products
  where merged_into is null and coalesce(catalog_included, true) and not coalesce(discontinued, false)
),
c as (
  select *,
    (source = 'maker' and source_url is not null) as confirmed,
    (case when type = 'cigar' then
        length_in is not null and ring_gauge is not null and expression is not null
        and (wrapper_leaf not in ('unknown', 'other') or wrapper_origin is not null)
        and binder is not null and filler is not null
        and country is not null and image_url is not null
      else
        proof is not null and spirit_type is not null and producer_id is not null and image_url is not null
      end) as complete
  from live
)
select type,
  count(*)                                                        as rows_live,
  count(*) filter (where confirmed)                               as rows_confirmed,
  round(100.0 * count(*) filter (where confirmed) / count(*), 1)  as pct_confirmed,
  count(*) filter (where complete)                                as rows_complete,
  round(100.0 * count(*) filter (where complete) / count(*), 1)   as pct_complete,
  count(*) filter (where confirmed and complete)                  as rows_confirmed_complete,
  round(100.0 * count(*) filter (where confirmed and complete) / count(*), 1) as pct_confirmed_complete,
  count(distinct brand)                                           as brands,
  count(distinct brand) filter (where confirmed)                  as brands_confirmed,
  count(distinct (brand, line))                                   as lines,
  count(distinct (brand, line)) filter (where confirmed)          as lines_confirmed,
  count(distinct source_url) filter (where confirmed)             as maker_pages,
  count(distinct regexp_replace(source_url, '^https?://([^/]+).*$', '\1')) filter (where confirmed) as maker_sites,
  count(*) filter (where confirmed and source_checked_at > now() - interval '120 days') as rows_fresh,
  round(100.0 * count(*) filter (where confirmed and source_checked_at > now() - interval '120 days')
        / nullif(count(*) filter (where confirmed), 0), 1)        as pct_fresh,
  count(*) filter (where facts_verified_at is not null)           as rows_audited,
  count(*) filter (where body is null and type = 'cigar')         as cigar_rows_no_body,
  count(*) filter (where wrapper_leaf in ('unknown','other') and wrapper_origin is null and type = 'cigar') as cigar_rows_no_wrapper
from c group by type;

grant select on cellar.catalog_scorecard to anon, authenticated;
