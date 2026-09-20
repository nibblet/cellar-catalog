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
- An origin or a shade alone never names a leaf: "Ecuador maduro" is `unknown`, not `other`.
- When the maker names only the origin, a new size takes the leaf its matched siblings in the
  same line already agree on (reported as "from siblings"), never a guess from elsewhere.
- Rows a human re-files go in the source's `OVERRIDES` so the run stays reproducible.
- When a maker publishes sizes only as an image, transcribe them into the source module and
  cite the image; never OCR-guess. Numeric size names ("460") are generic, never "moved lines".
- Sibling leaf inheritance only from siblings whose origin agrees with the maker's.
- A catalog line the site still lists by that exact name is never a size of a longer-named
  sibling ("Excalibur" No. 1 is not "Excalibur Cameroon" Lancelot).
- A maker that states the shape wins over the size name (`Vitola.shape`).
- A line page with no sizes is how General retires a line; treat those rows as discontinued.
- A maker's site is not exhaustive (Nub and Cain live elsewhere); use `--stale-only` for the
  rows that are genuinely gone or bogus instead of flagging every unmatched row.

## Measuring it

`SCORECARD.md` defines the metrics and targets (north star: rows confirmed by the maker *and*
card-complete), `targets.yml` is the brand queue, `REVIEW.md` is the quarterly runbook. The numbers
come from the `cellar.catalog_scorecard` view (`sql/`).

## Sources

| Site | Status |
|---|---|
| drewestate.com | done — 43 lines, 174 sizes, band + size images |
| kristoff.com | done — 22 lines, 93 sizes, box images |
| mayflowercigars.com | done — 4 lines, 12 sizes, one page per size |
| olivacigar.com | done — 16 lines, 95 sizes, size photos; wrapper by origin, leaf from the description |
| nubcigar.com | done — 11 lines (incl. Nub Cain), 28 sizes transcribed from the maker's line-up images |
| caincigar.com | parked domain; Cain lives on nubcigar.com in Nub sizes only |
| cigarworld.com | General Cigar's site; shared parser, one thin module per brand. Hoyo de Monterrey + Excalibur done (16 lines, 60 sizes). Punch, Cohiba, CAO next; Macanudo, Partagas, La Gloria Cubana after |
