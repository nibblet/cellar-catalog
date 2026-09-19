# cellar-catalog

Importers that keep the Cellar catalog (`cellar.products` in Supabase) in step with manufacturers'
own sites. One module per source; every row an importer touches gets `source = 'maker'` and a
`source_url`, and verified rows (`facts_verified_at`) are never overwritten.

## Shape

- `catalog/fetch.py` — polite fetcher: identifies itself, honours a per-host delay, caches to disk.
- `catalog/model.py` — what a source yields: a `LineRecord` (blend facts) with `Vitola`s (sizes).
- `catalog/normalize.py` — free text → the catalog's enums (wrapper leaf / origin / shade, strength, shape, dimensions). Deterministic; unknown stays unknown.
- `catalog/sources/<maker>.py` — one parser per site.
- `catalog/diff.py` — site records vs a catalog export → matched / corrections / additions / stale / aliases.
- `catalog/write.py` — a diff → SQL. Emits statements; never connects.

## Running a source

```bash
python3 scripts/crawl_drew_estate.py cache/drewestate            # fetch (10 s between pages)
python3 scripts/dry_run_drew_estate.py cache/drewestate export.json
python3 scripts/write_drew_estate.py cache/drewestate export.json <maker uuid> > import.sql
```

`export.json` is the current catalog rows for that maker's brands (see the query in
`scripts/dry_run_drew_estate.py`'s docstring for the shape). Review the dry run, then apply
`import.sql` in the Supabase SQL editor. Additions go in as `status = confirmed`; discontinued
rows are flagged, never deleted.

## Lessons baked in

- Match sizes in passes: exact name, then dimensions, then product-name-as-line, then a
  distinctive size that moved lines — and never claim the same catalog row twice.
- A catalog line can equal a maker's *size* (ACID Blondie is a size of the Blue series).
- Line names are aliases, not corrections, when both are right ("Unico" / "Unico Serie").
- Brand-agnostic line lookup is only for rows filed under a catch-all brand; "Undercrown /
  Maduro" must never answer to "Factory Smokes / Maduro".
- Export *all* of a maker's rows, not just those already bound to a `producer_id`.

## Sources

| Site | Status |
|---|---|
| drewestate.com | done — 43 lines, 174 sizes, band + size images |
| kristoff.com | next (WooCommerce, 25 lines) |
| mayflowercigars.com | next (BigCommerce, 4 lines, per-size pages) |
| olivacigar.com | next (13 lines; wrapper given by origin only) |
