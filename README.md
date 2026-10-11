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
| wildernesstraildistillery.com (bourbon) | blocked — no proof/age/mash text anywhere on the site |
| shop.penelopebourbon.com (bourbon) | done — 20 bottlings; 'Bourbon Facts' spec block on the brand's own Shopify store |
| smokewagon.com (bourbon) | done — 4 bottlings; low-yield, only Small Batch states a proof |
| oldelk.com (bourbon) | blocked — no proof/age/mash text anywhere on the site or in a rendered browser |
| barrellbourbon.com (bourbon) | done — 16 bottlings; current release then full batch history on one page, split at the 2nd "N proof" mention |
| starlightdistillery.com (bourbon) | done — 21 bottlings; WordPress, each page's own "Explore More Spirits" carousel truncated off before reading |
| rabbitholedistillery.com (bourbon) | done — 14 bottlings; the marketing site is the Shopify store, crawled via each product's own .json endpoint |
| garrisonbros.com (bourbon) | done — 15 bottlings; Rank Math Product JSON-LD, proof read from the body first since the schema value can lag a year |
| castleandkey.com (bourbon) | done — 6 bottlings; Shopify, proof/mash bill live only in the rendered page's Tasting Notes accordion |
| greenriverwhiskey.com (bourbon) | done — 10 bottlings; WordPress, proof read from either "(N proof)" or "[N PROOF]" |
| heavensdoor.com (bourbon) | done — 4 bottlings; Wix, rebranded since the seed (Refuge/Revival/Ascension/Revelation) |
| chickencockwhiskey.com (bourbon) | done — 12 bottlings; WordPress, collaboratively distilled at Bardstown Bourbon Company |
| yellowstonebourbon.com (bourbon) | done — 8 bottlings; WordPress, Limestone Branch Distillery |
| cedarridgedistillery.com (bourbon) | done — 35 bottlings parsed, 12 state a proof; WordPress, proof in three forms, flagship's 86 read from its own name |
| bluerunspirits.com (bourbon) | done — 14 bottlings; Drupal, Flight Series III is one page with six bottlings |
| breckenridgedistillery.com (bourbon) | done — 17 bottlings; WordPress, carousel of other spirits truncated off |
| fourgatewhiskey.com (bourbon) | done — 37 batch bottlings; Duda, stale slugs so the page heading names the bottling |
| highwest.com + ship.highwest.com (bourbon) | done — 15 bottlings; Shopify shell, facts from the sibling store and the compliance list |
| ourwolfspirit.com / IJW (bourbon) | done — 5 Puncher's Chance bottlings from the brand's Shopify collection JSON |
| jepthacreed.com, oregonspiritdistillers.com, pinhookbourbon.com, redemptionwhiskey.com, yellowrosedistilling.com (bourbon) | done — 7 / 9 / 27 / 12 / 7 bottlings |
| clydemays.com, distillery291.com, docswhiskey.com, copperandkings.com (bourbon) | done — 3 / 15 / 27 / 2 bottlings |
| oldelk.com, wildernesstraildistillery.com (bourbon) | done — unparked: Old Elk was rebuilt, Wilderness Trail's proof is on its FAQ |
| stellum.com, 2xowhiskey.com (bourbon) | done — proof read by hand from the maker's own bottle-label photos (Stellum 7 of 9 rows, 2XO American Oak) |
| jeffersonsbourbon.com (bourbon) | done, hand-read — the host blocks the importer; four pages read in the app's browser pane with the owner's approval and cached by hand (cache/jef is committed) |
| bluegrassdistillers.com, asmithbowman.com (bourbon) | done — 8 / 29 rows; Bowman is 21 historical Abraham Bowman releases plus the core line |
| shortbarrelbourbon.com, whistlepigwhiskey.com, rd1spirits.com, hardtruth.com, bluenotebourbon.com (bourbon) | done — 10 / 14 / 6 / 30 / 11 rows |
| luckysevenspirits.com, lexingtonbrewingco.com (Town Branch), boonedistilling.com, horsesoldierbourbon.com, hkyoungbourbon.com (bourbon) | done — 11 / 14 / 11 / 10 / 3 rows |
| drinkmhs.com (Fireside) (bourbon) | done — 13 bottlings from the catalogue array in the site's public JS bundle (every URL serves one empty SPA shell) |
| pursuitspirits.com, watchhillwhiskeyco.com, klukewhiskeycompany.com, calumetbourbon.com, backbonebourbon.com, brothersbondbourbon.com, journeyman.com, boundaryoak.co (bourbon) | done — 8 makers, 44 bottlings added, 25 rows corrected, 2 more confirmed; mostly labelled spec blocks, K.Luke's from a batch ledger |
| smoothambler.com, driftlessglen.com, jeffersonsbourbon.com, kentuckyowl.com, stellum.com, 2xowhiskey.com (bourbon) | blocked or no proof stated — see targets.yml |
| us.davidoffgeneva.com | done — Davidoff, Avo, Camacho, Zino, Zino Platinum: 191 rows from BigCommerce custom fields + metafields via the store's own server action (6 requests, no page crawl). Origins for wrapper/binder/filler and a 0–5 intensity per product; country from an approved per-brand map |
| myfathercigars.com | done — My Father, Don Pepin Garcia, Flor de las Antillas, El Centurion, Jaime Garcia, La Dueña, La Antiguedad, Fonseca, Tabacos Baez: 130 sizes from 26 line pages (`<h3>Name L x R</h3>` under each cigar image). Blend line gives wrapper/binder/filler; "Handcrafted in …" gives country per page (three lines are USA or Honduras, not Nicaragua) |
| rockypatel.com | done — Rocky Patel, Java, Nish Patel: 189 sizes from 42 line pages (a "Cigar Details" block in five formats). Country and mild/medium/full body from the maker's Honduran / Nicaraguan collection pages (its `cigar-category` taxonomy); wrapper/binder/filler from the block where stated, else from the page copy's "… wrapper" sentence, tobacco words only |
| perdomocigars.com | done — Perdomo: 135 sizes from 9 line pages, a section per wrapper with wrapper / binder / filler / Strength and "Name • L x R" sizes. One line per page, wrapper in the size name. Country company-wide from The Perdomo Way (facilities in Estelí). Five lines are image galleries only |
| gurkhacigars.com | done — Gurkha: 87 sizes from 38 line pages. A Blend block states Wrapper / Binder / Filler / Origin (country per line from the maker), then Sizes ("Koi - 4x58", fractions split by markup) and Strength. Collector's Corner private blends have no blend or sizes |
| ashtoncigar.com, laaromadecuba.com | done — Ashton (10 lines) and La Aroma de Cuba (9 lines), one shared Drupal 7 template: a `data-dimensions`/`data-shapename` attribute pair per size, and a "Product Details" block for Strength/Country/Wrapper. Binder and filler come from the page's own description prose, only when it names an origin explicitly — the prose sits before the "Product Details" heading on Ashton's pages but after it on La Aroma de Cuba's, so both windows are searched. San Cristobal (sancristobalcigar.com), a separate, newer site under the same Ashton Distributors umbrella, is blocked: it 403s the project's crawler UA while a browser UA gets 200 |
| alecbradley.com | done — 47 lines, 169 sizes. Nuxt 3 + Strapi: every page embeds its full product record as a devalue-serialized JSON payload (wrapper/binder/filler/body as plain fields, sizes as a markdown list), no HTML text-scraping. Fine & Rare's eight annual limited releases are filed under one "Fine & Rare" line via the page's own `parent` field, the release code folded into the size name. No page states where the cigars are rolled, so country stays unknown throughout |
| altadisusa.com | done — Montecristo (26 lines), Romeo y Julieta (24 lines) and H. Upmann (8 lines) of the site's 16 brands. WordPress; each page states origin/wrapper/binder/filler as labelled spec tiles, sizes as a "Name: A x B" list — mostly ring-gauge-first, but not consistently, so the parser trusts whichever number reads as a plausible ring gauge over position. Every product title stutters the brand name ("Montecristo Epic", "Espada by Montecristo"); stripped the way `drew_estate.py` strips its own repeated brand lead-in, except when the brand's own prefix spelling varies ("H.Upmann" without the period's space on one H. Upmann page), handled with a per-brand list of prefix spellings. The site's wp-sitemap 404s in stretches while every product page keeps loading fine; a `FALLBACK_URLS` list of the three brands' known pages covers a crawl or write when that happens |
| joyacigars.com | done — 18 lines, 84 sizes. WordPress; a disclosed "N/5" strength tile maps cleanly to mild-full, wrapper/binder/filler as plain tiles (one line's wrapper is literally "Confidential"). Sizes found by scanning for any line that reads as dimensions, since there's no reliable bounding heading. Also publishes a parallel `/es/cigars/...` Spanish mirror of every page, skipped. Country curated brand-wide from the homepage's own "made in Nicaragua...headquarters in Estelí" statement |
| arturofuente.com | done — 15 line pages, 139 rows (wrapper codes N/M/S/SG/RSG/C read from usage; no legend). Binder/filler stated only for OpusX, Casa Cuba, Especiales, so most rows are confirmed but incomplete |
| padron.com | done — 7 series, 56 sizes → 106 rows (one per wrapper: natural / maduro). Blend facts cited from the maker's Vertical Integration page; Special Releases publish no sizes |
| cigarworld.com | General Cigar's site; shared parser, one thin module per brand. Done: Hoyo de Monterrey + Excalibur (16 lines, 60 sizes), Punch (28, 95), Cohiba (28, 75), CAO (66, 176), Macanudo (39, 137), Partagas (20, 84), La Gloria Cubana (34, 107), Diesel (29, 60). Every General brand on the site is covered |
| tatuajecigars.com | done — Tatuaje: 20 lines, 114 sizes from 19 pages. Small static legacy site, no CMS or sitemap — URLs come from the homepage's own "Smokes" nav grid, hardcoded as a slug list. Company catch-all brand covers Cabaiguan, La Riqueza, El Triunfador, Ambos Mundos, La Casita Criolla, Fausto, Havana VI, Seleccion de Cazador alongside the core Tatuaje lines. WRAPPER/BINDER/FILLER and COUNTRY OF ORIGIN are plain labelled tiles; STRENGTH is a 1-5 scale marked by a `strength-active` span. The Cabaiguan Guapos page states its blend block twice, once per Natural/Maduro tag, split into one record per tag |
| plasenciacigars.com | done — Plasencia: 9 lines, 33 sizes. WordPress with a custom "collection" post type, one page per line, each with an owl-carousel gallery (size name, shape, dims, its own photo) plus a shared spec table and a leaf-icon strength meter. The per-size `/cigar/` landing pages carry no data at all — hero image and title only — so only the 9 collection pages are crawled. The spec table's "Origin" field is inconsistent (a country, a factory name, or a two-country blend joined by "&"); country is read from it only when it resolves to exactly one known country name |
| aganorsaleaf.com | done — Aganorsa Leaf, JFR, and 3 Warped lines: 25 site lines, 105 sizes from 17 pages. WordPress + Elementor (PowerPack "Advanced Tabs"); no cigar sitemap, hand-listed from the "Cigars" nav. Several wrapper variants sit as tabs on one page (Corojo/Maduro/Connecticut/25th...), each its own Blend Summary + size block, wrapper folded into each size's own name; other conceptual lines split across separate pages instead (JFR Corojo/Maduro/Connecticut; Lunatic Habano/Maduro; the three Guardian of the Farm releases), unified via a small slug table. "Lunatic"/"JFR" file under the existing "JFR" brand, "Guardian of the Farm" (a Warped collaboration) under "Warped" — the rest of Warped's own catalog awaits its own warpedcigars.com import. Strength is a scale image whose filename encodes the number. Country stays unknown throughout: the site only says cigars are rolled "in our factories in Nicaragua and Miami" without saying which per product |
| casacarrillocigars.com | done — E.P. Carrillo: 18 lines, 51 sizes. epcarrillo.com now redirects here (a 2025 rebrand). WordPress + WPBakery; no cigar sitemap and no clean product index in the page sitemap, so the line list is hand-curated from the site's own "all-products" page plus three newer releases not yet listed there. Sizes are a plain "Name: L x R" list; Tobaccos gives Origin/Wrapper/Binder/Filler each on its own line after the label; Strength is a "Strength – Word" heading that can sit anywhere on the page. A few limited releases state one size under a bare "Size:" label, sometimes unnamed. Origin is always "Dominican Republic", used directly as country. "Encore Black", "Legacy League" (a loyalty program) and "Pledge of Allegiance" publish nothing readable and are skipped |
