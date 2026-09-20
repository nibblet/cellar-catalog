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
python3 scripts/crawl.py kristoff cache/kristoff                 # fetch (polite delay per source)
python3 scripts/dry_run.py kristoff cache/kristoff export.json
python3 scripts/write.py kristoff cache/kristoff export.json out/ [--maker <uuid>] [--country "..."]
```

`export.json` is the current catalog rows for that maker's brands (see the query in
`scripts/dry_run.py`'s docstring for the shape). Review the dry run, then apply `out/part1.sql`
(corrections, aliases, discontinued) and each `out/inserts_N.sql` batch in the Supabase SQL
editor. Batches stay under the 100 KB statement limit. Additions go in as `status = confirmed`; discontinued
rows are flagged, never deleted.

## Lessons baked in

- Match sizes in passes: exact name, then dimensions, then product-name-as-line, then a
  distinctive size that moved lines — and never claim the same catalog row twice.
- A catalog line can equal a maker's *size* (ACID Blondie is a size of the Blue series).
- Line names are aliases, not corrections, when both are right ("Unico" / "Unico Serie").
- Brand-agnostic line lookup is only for rows filed under a catch-all brand; "Undercrown /
  Maduro" must never answer to "Factory Smokes / Maduro".
- Export *all* of a maker's rows, not just those already bound to a `producer_id`.
- A fuzzy line match must agree on wrapper family: "Kristania" (maduro) is "Kristania Maduro",
  not "Kristania Criollo". When a catalog line is a prefix of several site lines, rename it.
- Sizes a maker leaves unnamed are kept as dimension strings ("6x60"), never invented names.
- Sizeless, expression-less rows whose line exists are placeholders — report, don't touch.
- A maker with one page per size gives a `group()` hook to fold pages into lines; each row
  keeps its own page as `source_url`.
- Country only when the maker (or the owner) states it; never inferred from the filler.

## Sources

| Site | Status |
|---|---|
| drewestate.com | done — 43 lines, 174 sizes, band + size images |
| kristoff.com | done — 22 lines, 93 sizes, box images |
| mayflowercigars.com | done — 4 lines, 12 sizes, one page per size |
| olivacigar.com | next (13 lines; wrapper given by origin only) |
