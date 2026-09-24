-- Applied to Supabase as migration "catalog_admin" on 2026-09-24. Kept as the record.
--
-- Backing tables for the catalog admin UI (admin/):
--   product_edits  every change to a product row, written by trigger — who, when, before, after.
--                  changed_by is null for importer SQL run in the SQL editor.
--   audit_checks   REVIEW.md step 4: one row per hand-checked product, so audit accuracy is a query.

create table if not exists cellar.product_edits (
  id          bigint generated always as identity primary key,
  product_id  uuid not null references cellar.products(id),
  changed_by  uuid,
  changed_at  timestamptz not null default now(),
  before      jsonb not null,
  after       jsonb not null
);
create index if not exists product_edits_product on cellar.product_edits (product_id, changed_at desc);
create index if not exists product_edits_recent on cellar.product_edits (changed_at desc);

alter table cellar.product_edits enable row level security;
drop policy if exists product_edits_admin_read on cellar.product_edits;
create policy product_edits_admin_read on cellar.product_edits for select to authenticated
  using (cellar.is_admin());
grant select on cellar.product_edits to authenticated;

-- Only the columns that changed; bookkeeping stamps and the large AI-derived blobs are left out.
create or replace function cellar.log_product_edit() returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  o jsonb := to_jsonb(old);
  n jsonb := to_jsonb(new);
  b jsonb := '{}';
  a jsonb := '{}';
  k text;
begin
  for k in select jsonb_object_keys(n) loop
    if k not in ('updated_at', 'source_checked_at', 'wheel_vector', 'trait_vector', 'winston_prose')
       and o -> k is distinct from n -> k then
      b := b || jsonb_build_object(k, o -> k);
      a := a || jsonb_build_object(k, n -> k);
    end if;
  end loop;
  if a <> '{}'::jsonb then
    insert into cellar.product_edits (product_id, changed_by, before, after)
    values (new.id, auth.uid(), b, a);
  end if;
  return null;
end $$;
revoke all on function cellar.log_product_edit() from public;

drop trigger if exists products_log_edit on cellar.products;
create trigger products_log_edit after update on cellar.products
  for each row execute function cellar.log_product_edit();

create table if not exists cellar.audit_checks (
  id          bigint generated always as identity primary key,
  product_id  uuid not null references cellar.products(id),
  quarter     text not null,                 -- '2026-Q4'
  confirmed   boolean not null,              -- the row was maker-confirmed when checked
  correct     boolean not null,              -- false = a fact was wrong (and corrected)
  note        text,
  checked_by  uuid default auth.uid(),
  checked_at  timestamptz not null default now()
);
create index if not exists audit_checks_quarter on cellar.audit_checks (quarter);

alter table cellar.audit_checks enable row level security;
drop policy if exists audit_checks_admin on cellar.audit_checks;
create policy audit_checks_admin on cellar.audit_checks for all to authenticated
  using (cellar.is_admin()) with check (cellar.is_admin());
grant select, insert, update, delete on cellar.audit_checks to authenticated;

-- merge_product is security invoker, which is right for the SQL editor but, called by an admin
-- through the API, row-level security would silently skip other members' saves, tastings and
-- pairings. The admin UI calls this wrapper instead. (Applied as migration "catalog_admin_merge".)
create or replace function cellar.admin_merge_product(child uuid, parent uuid, release text default null)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not cellar.is_admin() then
    raise exception 'admin only';
  end if;
  perform cellar.merge_product(child, parent, release);
end $$;
revoke all on function cellar.admin_merge_product(uuid, uuid, text) from public, anon;
grant execute on function cellar.admin_merge_product(uuid, uuid, text) to authenticated;
