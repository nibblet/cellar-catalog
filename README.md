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
- The maker's copy often names the leaf its wrapper field only regionalises ("Honduran" + "Habano
  wrapper" in the description); read it. When even the copy names only a region, the leaf stays
  unknown — Cigar World's tobacco pages are listings, not definitions.
- Country comes from the copy ("handmade in Nicaragua", "STG Estelí") when it is there; a curated
  per-line map is the documented fallback, never a brand-wide guess.
- A maker's site is not exhaustive (Nub and Cain live elsewhere); use `--stale-only` for the
  rows that are genuinely gone or bogus instead of flagging every unmatched row.

## Measuring it

`SCORECARD.md` defines the metrics and targets (north star: rows confirmed by the maker *and*
card-complete), `targets.yml` is the brand queue, `REVIEW.md` is the quarterly runbook. The numbers
come from the `cellar.catalog_scorecard` view (`sql/`).

## Bourbon

The bourbon track (distillery sites → `cellar.products` typed columns) is described in `BOURBON.md`;
its pieces live in `catalog/bourbon/` and `catalog/sources/bourbon/`, and `scripts/export.py` pulls the
rows to diff against over PostgREST.

## Sources

| Site | Status |
|---|---|
| drewestate.com | done — 43 lines, 174 sizes, band + size images |
| kristoff.com | done — 22 lines, 93 sizes, box images |
| mayflowercigars.com | done — 4 lines, 12 sizes, one page per size |
| olivacigar.com | done — 16 lines, 95 sizes, size photos; wrapper by origin, leaf from the description |
| nubcigar.com | done — 11 lines (incl. Nub Cain), 28 sizes transcribed from the maker's line-up images |
| caincigar.com | parked domain; Cain lives on nubcigar.com in Nub sizes only |
| buffalotracedistillery.com (bourbon) | done — 68 bottlings across 22 families; proof, class, named mash bill, bottle shot per page |
| jimbeam.com + 4 Beam sites (bourbon) | done — 97 bottlings, 12 families; schema.org Product, PROOF note or prose |
| heavenhilldistillery.com + elijahcraig.com (bourbon) | done — 34 bottlings, 12 families; Proof:/Age: block |
| oldforester.com, woodfordreserve.com, jackdaniels.com, cooperscraft.com (bourbon) | done — 63 bottlings, 4 families; proof from the product's own copy or a Proof note |
| wildturkeybourbon.com + russellsreserve.com (bourbon) | done — 25 bottlings; PROCESS teaser |
| fourrosesbourbon.com (bourbon) | done — 10 bottlings from 24 pages; one Proof / Aged line |
| 1792bourbon.com (bourbon) | done — 8 bottlings from 8 static pages; proof in the copy or footer |
| bulleit.com, georgedickel.com → thebar.com (bourbon) | done — 28 bottlings, 4 families; Diageo's own store is the maker's page for Dickel, Blade and Bow, I.W. Harper |
| rebelbourbon.com, ezrabrooks.com, luxrowdistillers.com (bourbon) | done — 23 bottlings, 7 families; product pages and brand pages with a tab per variant |
| michters.com (bourbon) | done — 19 bottlings, 3 families; BOTTLING STRENGTH block, one block per year on Legacy pages |
| angelsenvy.com (bourbon) | done — 9 bottlings; schema.org Product, proof in prose; the two flagships state none |
| jeffersonsbourbon.com (bourbon) | blocked — Cloudflare challenge, and the pages state no proof |
| kentuckybourbonwhiskey.com (bourbon) | done — 14 bottlings across 8 family brands (Willett, Rowan's Creek, Noah's Mill, Johnny Drum, Pure Kentucky, Kentucky Vintage, Speakeasy) |
| newriffdistilling.com (bourbon) | done — 24 bottlings, structured Age/Proof line |
| bardstownbourbon.com (bourbon) | done — 7 bottlings; Origin Series + 3 Distillery Reserve finishes + current Discovery |
| widowjane.com (bourbon) | done — 10 bottlings; 'AGED N YEARS', 'M PROOF' tag pills |
| kentuckypeerless.com (bourbon) | blocked — every figure is baked into label photography, no text data at all |
| unclenearest.com (bourbon) | done — 9 bottlings; proof in prose |
| us.davidoffgeneva.com | done — Davidoff, Avo, Camacho, Zino, Zino Platinum: 191 rows from BigCommerce custom fields + metafields via the store's own server action (6 requests, no page crawl). Origins for wrapper/binder/filler and a 0–5 intensity per product; country from an approved per-brand map |
| myfathercigars.com | done — My Father, Don Pepin Garcia, Flor de las Antillas, El Centurion, Jaime Garcia, La Dueña, La Antiguedad, Fonseca, Tabacos Baez: 130 sizes from 26 line pages (`<h3>Name L x R</h3>` under each cigar image). Blend line gives wrapper/binder/filler; "Handcrafted in …" gives country per page (three lines are USA or Honduras, not Nicaragua) |
| rockypatel.com | done — Rocky Patel, Java, Nish Patel: 189 sizes from 42 line pages (a "Cigar Details" block in five formats). Country and mild/medium/full body from the maker's Honduran / Nicaraguan collection pages (its `cigar-category` taxonomy); wrapper/binder/filler from the block where stated, else from the page copy's "… wrapper" sentence, tobacco words only |
| perdomocigars.com | done — Perdomo: 135 sizes from 9 line pages, a section per wrapper with wrapper / binder / filler / Strength and "Name • L x R" sizes. One line per page, wrapper in the size name. Country company-wide from The Perdomo Way (facilities in Estelí). Five lines are image galleries only |
| gurkhacigars.com | done — Gurkha: 87 sizes from 38 line pages. A Blend block states Wrapper / Binder / Filler / Origin (country per line from the maker), then Sizes ("Koi - 4x58", fractions split by markup) and Strength. Collector's Corner private blends have no blend or sizes |
| ashtoncigar.com, laaromadecuba.com | done — Ashton (10 lines) and La Aroma de Cuba (9 lines), one shared Drupal 7 template: a `data-dimensions`/`data-shapename` attribute pair per size, and a "Product Details" block for Strength/Country/Wrapper. Binder and filler come from the page's own description prose, only when it names an origin explicitly — the prose sits before the "Product Details" heading on Ashton's pages but after it on La Aroma de Cuba's, so both windows are searched. San Cristobal (sancristobalcigar.com), a separate, newer site under the same Ashton Distributors umbrella, is blocked: it 403s the project's crawler UA while a browser UA gets 200 |
| alecbradley.com | done — 47 lines, 169 sizes. Nuxt 3 + Strapi: every page embeds its full product record as a devalue-serialized JSON payload (wrapper/binder/filler/body as plain fields, sizes as a markdown list), no HTML text-scraping. Fine & Rare's eight annual limited releases are filed under one "Fine & Rare" line via the page's own `parent` field, the release code folded into the size name. No page states where the cigars are rolled, so country stays unknown throughout |
| arturofuente.com | done — 15 line pages, 139 rows (wrapper codes N/M/S/SG/RSG/C read from usage; no legend). Binder/filler stated only for OpusX, Casa Cuba, Especiales, so most rows are confirmed but incomplete |
| padron.com | done — 7 series, 56 sizes → 106 rows (one per wrapper: natural / maduro). Blend facts cited from the maker's Vertical Integration page; Special Releases publish no sizes |
| cigarworld.com | General Cigar's site; shared parser, one thin module per brand. Done: Hoyo de Monterrey + Excalibur (16 lines, 60 sizes), Punch (28, 95), Cohiba (28, 75), CAO (66, 176), Macanudo (39, 137), Partagas (20, 84), La Gloria Cubana (34, 107), Diesel (29, 60). Every General brand on the site is covered |
