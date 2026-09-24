# Bourbon track

How the bourbon catalog gets to first in class, and stays there. The cigar track (README.md,
SCORECARD.md, REVIEW.md) is the model; this is the bourbon-specific part. One rule above all:
**after Phase 0, no bourbon fact is hand-fixed outside the in-app editor.** Everything else comes
from a maker's page through an importer, so the same correction never has to be made twice.

## Where it started (2026-09-21)

2,110 bourbon rows, every one from a third party: the bourbonExplorer CSV (spring 2026, ~1,350 rows,
GPT-4 "enhanced"), the Breaking Bourbon crawl (2026-09-19, 2,405 review pages → 1,699 rows with a
`source_url`), 24 manual rows, 6 AI rows. `source = 'maker'`: 0. Scorecard: 307 live, 72% complete,
0% confirmed.

The shelf itself was wrong in ways provenance can't show: Buffalo Trace, Eagle Rare, Woodford
Reserve, Elijah Craig Small Batch, Booker's, Bulleit, George Dickel and Jack Daniel's were hidden
by the May cut-back while their lottery-tier siblings were shown; the same bottle sat on both sides
of the `catalog_included` line under two names (Eagle Rare / Eagle Rare 10 Year Single Barrel,
W.L. Weller 12 / Weller 12, Maker's 46 / No. 46 French Oaked); Elijah Craig still said 12 years.

## Phase 0 — the last hand-fix (done 2026-09-21, `sql/20260921_bourbon_phase0.sql`)

19 soft merges through `cellar.merge_product`, 52 flagships promoted, stale facts corrected, rarity
on every live row, anniversaries and experiments cleared from `is_core_range`, every member-saved
bottle made browsable. 374 live rows after. Nothing deleted; nothing verified touched; nothing
stamped `facts_verified_at`, so the importers can still overwrite these from the maker's page.

## Phase 1 — maker importers (Q4 2026)

Same shape as the cigar importers, bourbon-specific pieces under `catalog/bourbon/`:

- `model.py` — a `BottlingRecord`: one per bottling (the SKU a member orders by name). Batches,
  years and picks are never records; they live on the bottle.
- `normalize.py` — label text → typed columns: proof ("90 (45%)", "45% ABV"), age ("Aged 10 Years",
  "12-year-old", "a full decade"; never NAS from silence), spirit type from the class statement,
  mash style only from a stated recipe or a named mash bill the source module maps, BiB / barrel
  proof from the label words and the app's 115-proof floor, finish, the bar-order name
  (`titlecase`), and `expression_key` so "Aged 10 Years" ~ "10 Year" ~ "10 Yr".
- `diff.py` — a bottling claims at most one catalog row in its family: same expression key or
  flagship on both sides; then the maker's name or title variant equals the row's name or an alias;
  then one expression key inside the other with the proofs agreeing. Rows with a `release_label`
  are variants and are never claimed. Corrections: proof, a stated age, spirit type, mash style,
  a stated mash bill, BiB / barrel proof (only up), a finish, an MSRP, an image the row lacks,
  and the maker's name (the old name becomes an alias).
- `write.py` — corrections as updates guarded by `facts_verified_at is null`; additions as
  `jsonb_to_recordset` batches guarded by the family/expression unique key; every row the maker
  still lists stamped `source_checked_at`; a row the maker agrees with outright becomes
  `source = 'maker'`; stale rows flagged discontinued only when passed `--stale-only`.
- `catalog/sources/bourbon/<maker>.py` — one parser per site. It owns the slug/brand → family map,
  the (brand, title) refiles, the named-mash-bill map, and the "not core" pattern.

Run a source:

```bash
export CELLAR_ENV_FILE=/path/to/.env.local            # SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
python3 scripts/crawl.py bourbon.buffalo_trace cache/bt
python3 scripts/export.py --type bourbon --source bourbon.buffalo_trace cache/bt-export.json
python3 scripts/bourbon_dry_run.py bourbon.buffalo_trace cache/bt cache/bt-export.json
python3 scripts/bourbon_write.py bourbon.buffalo_trace cache/bt cache/bt-export.json out/bt --maker <uuid> [--stale-only id,id]
```

Read the dry run, apply `part1.sql` then each `inserts_N.sql`, re-run the scorecard.

### Tier 1 — what a US shelf is made of

| Producer | Site | Families |
|---|---|---|
| Buffalo Trace (Sazerac) | buffalotracedistillery.com/our-brands | Buffalo Trace, Eagle Rare, Weller, Blanton's, E.H. Taylor, Stagg, Sazerac, Benchmark, Elmer T. Lee, Van Winkle, Traveller, Old Charter |
| Beam Suntory | jimbeam.com, knobcreek.com, makersmark.com, basilhayden.com, bookersbourbon.com | Jim Beam, Knob Creek, Maker's Mark, Basil Hayden, Booker's, Baker's, Old Grand-Dad, Legent |
| Heaven Hill | heavenhilldistillery.com, evanwilliams.com, elijahcraig.com, larcenybourbon.com | Evan Williams, Elijah Craig, Larceny, Henry McKenna, Old Fitzgerald, Rittenhouse, Pikesville, Bernheim |
| Brown-Forman | oldforester.com, woodfordreserve.com, jackdaniels.com | Old Forester, Woodford Reserve, Jack Daniel's, Coopers' Craft |
| Campari | wildturkeybourbon.com, russellsreserve.com | Wild Turkey, Russell's Reserve |
| Four Roses (Kirin) | fourrosesbourbon.com | Four Roses |
| Barton (Sazerac) | 1792bourbon.com | 1792, Very Old Barton |
| Diageo | bulleit.com, georgedickel.com → thebar.com (Diageo's store) | Bulleit, George Dickel, Blade and Bow, I.W. Harper |
| Lux Row / MGP | luxrowdistillers.com, rebelbourbon.com | Rebel, Ezra Brooks, Old Ezra, Daviess County, Blood Oath |
| Michter's | michters.com | Michter's |
| Angel's Envy (Bacardi) | angelsenvy.com | Angel's Envy |
| Jefferson's | jeffersonsbourbon.com | Jefferson's |

Tier 2 (Q1 2027): Willett, New Riff, Bardstown Bourbon Co, Widow Jane, Uncle Nearest, Penelope, Smoke
Wagon, Barrell done 2026-09-24; Peerless, Wilderness Trail, Old Elk blocked (no machine-readable spec
data); next: Starlight, Garrison Brothers, Rabbit Hole, Castle & Key, Green River, Chicken Cock, Heaven's
Door, Yellowstone.

The queue lives in `targets.yml` under `bourbon:`.

### What a maker's page gives that a review can't

Current proof and age (a review is frozen at its date; Elijah Craig's 12 sat in the catalog for
nine years after the label dropped it), a bottle shot for every row (102 live rows had none),
and discontinuation — a bottling gone from the maker's page is the stale signal, the same as a
cigar line gone from its site.

### Lessons from the first three sources

- A maker's page that states no proof cannot create a row; the dry run says so and the writer skips it.
- A proof *range* ("107–114", "bottled between 108 and 114 proof") is not a statement; it reads as none.
- An age range the label doesn't print ("8–12 Years Old") is a display label, never `age_years`.
- Batches and chapters are one bottling: every Booker's batch page folds into Booker's (the latest
  batch supplies proof and age), Little Book's chapters into Little Book. The dry run's STALE list is
  where the catalog's own release-as-row duplicates surface; merge them by hand with
  `cellar.merge_product` and record it in `sql/`.
- Family comes from the URL (slug or host), never from the page's brand line: collection pages
  print the collection where the brand goes.
- Judgment lives in the source module's tables — `REFILE` (slug → family/expression/aliases),
  `CLASS_BY_SLUG` / `FAMILY_CLASS`, `NOT_CORE`, `RARITY`, `MASH_BILLS` — so a re-run reproduces it.
- Proof is read only from the product's own copy. Every Jack Daniel's page promotes "100 proof"
  Bonded; every Old Forester page names its "86 Proof" and "100 Proof" siblings; a barrel *entry*
  proof ("entering the second barrel at 100 proof") is not a bottling proof.
- A generic name that fits two specific ones fits neither: "117 Series" is not Warehouse K when the
  site also lists Warehouse H, and "Master's Collection" is not Sweet Oak when the catalog also
  holds Batch Proof. Such rows stay unmatched and show in STALE for a human to decide.
- A row the maker still lists is not discontinued, and if it is core range it is browsable: the
  importer clears `discontinued` and applies the promotion pass on every matched row.
- Verified rows stay verified: the dry run shows "[verified — will be skipped]" and the SQL is guarded.
  When the maker disagrees with a verified row, that is an audit item, not an importer change.
- A maker's own store is the maker's page: Diageo sells George Dickel, Blade and Bow and I.W. Harper
  only through thebar.com, and georgedickel.com redirects there. A redirect that lands on a brand or
  recipes page (Dickel 18 Year, Classic Recipe) is not a product page — the canonical link says where
  it landed, and the parser returns nothing.
- A law's minimum is not an age: the store's Bottled-in-Bond Act paragraph says "a minimum of four
  years" on a 7-year bottling; the single-malt definition says "distilled to 160 proof or less". Both
  paragraphs are stripped before reading. The one entry-proof exception: 1792 Full Proof is bottled at
  its barrel entry proof, and the page says so.
- "Aged between 10 and 12 years" is a display label (`normalize.age` returns it as one); a store's
  tasting notes can quote a sibling ("I.W. Harper 15-Year-Old"), so age is read from the title and
  description only.
- A page that lists every year's release (Michter's Legacy Series, Blood Oath's pacts) is one bottling:
  the first block is the current release and supplies proof, age and image; the catalog's per-year rows
  fold into it with `cellar.merge_product(child, parent, 'Pact No. 7')`, which keeps the release label.
- A barrel-strength page that states a *range* for the year ("ranged from 107.4 to 115.2 proof") states
  no proof; one that states the year's *average* ("109.1 proof") does. A brand that states one proof for
  all its variants ("Like all Daviess County variants … is 96 proof") states it for each tab; a proof the
  page prints only as an image whose file name spells it out ("50-100_proof.png") is still the maker's.
- A page the site keeps but its own lineup navigation no longer links (Rebel's 2020 French Oak Finish,
  Ezra Brooks' 90-proof Straight Rye) is history, not a listing; the lineup index or nav is the list.
- A matched row is confirmed (`source = 'maker'`) only when the page states its proof. Angel's Envy's
  flagship pages state none: the importer still records the maker page, name, finish and image, but the
  row keeps its seed source until a page (or a COLA) states the proof. The dry run says
  "[no proof stated — listed, not confirmed]".
- A site behind a Cloudflare challenge (jeffersonsbourbon.com, legentbourbon.com) is parked, not
  worked around with a browser: read by hand, Jefferson's pages state no proof anyway.
- One domain can host several of a family's shelf brands with no subdomain to key off (Willett's
  kentuckybourbonwhiskey.com carries Rowan's Creek, Noah's Mill, Johnny Drum, Pure Kentucky, Kentucky
  Vintage and Willett itself). Family is the product's own brand name, same as Lux Row's tab pages;
  a seed row filed under the wrong family for this reason doesn't match by family, so it surfaces as
  both a STALE row and a same-bottling ADDITION under the correct family — merge the STALE row into the
  new one after the insert runs, by name/proof correspondence, same as any batch-row merge.
- A single-barrel "selection" or "cigar club pick" page describes a program, not a bottling: it states
  no proof, because every actual barrel differs. Skip crawling it rather than adding a proof-less row.
- Two real bugs in `catalog/bourbon/normalize.py:spirit_type()`, both the same shape: it checked the
  combined class+name text for a disqualifying word, and a maker's own free-text name can innocently
  contain one. Bardstown Bourbon Company's own name contains "Bourbon", so its rye was reading as
  spirit_type=bourbon; Widow Jane's "Tequila Ocho Cask Finish" bourbon contains "tequila", so it was
  being skipped as not-whiskey by the vodka/gin/tequila/rum exclusion. Both checks now key off
  `class_raw` (the label's own class statement) alone — never the marketing name, which can legitimately
  reference another spirit's cask without being that spirit. Re-verify every applied source's dry run
  after touching `normalize.py`; both fixes were confirmed clean across all sources applied so far.
- Some sites keep no text data at all: Kentucky Peerless bakes every proof, age and mash figure into
  label photography and renders its section titles as canvas glyphs, so nothing about a bottling is
  machine-readable, even in a rendered browser. Confirm with the browser pane (screenshot showing text
  that `document.body.textContent` doesn't contain is the tell) before concluding a site is unworkable,
  then park it next to Jefferson's rather than attempting OCR. Wilderness Trail is the same story without
  even the photography: the copy is genuine marketing prose with no numbers in it anywhere.
- A brand's own store can be a wholly different, better site than its marketing domain: Penelope's
  penelopebourbon.com (WordPress) rarely states a number, but shop.penelopebourbon.com (Shopify) carries
  a "Bourbon Facts" spec block with Proof, Age and Mash Bill on every product page — check the shop
  subdomain before concluding a brand's numbers aren't published. Shopify's own `/products.json` is a
  clean way to enumerate handles; the per-product HTML page (not the JSON's marketing `body_html`) is
  where the spec block lives.
- A maker's site can have its own content-entry error: Penelope's Barrel Strength page has its proof
  sitting in the "Type & Process" field instead of "Proof". Read whichever field states the number rather
  than trusting the label, and don't assume every field means what its heading says.
- A domain named after the brand can be a parked placeholder: smokewagonwhiskey.com is; the real site is
  smokewagon.com. Check before concluding a site doesn't exist.
- A site can be proud of *how* it makes proof without ever stating *what* the proof is: Old Elk markets
  its "Slow Cut" proofing process at length on every page and gives a mash bill for exactly one product
  (Wheat Whiskey), but no page states a number, confirmed in a rendered browser too. Blocked the same way
  as Wilderness Trail — marketing prose with the actual figures held back, not a technical barrier.
- A Squarespace or Wix nav "folder" page (a category landing with child pages under it, like Old Elk's
  /lineup or /specialty-products) is often a bare shell with an intro paragraph and no per-product data;
  the real content lives on the child pages the folder links to, not the folder page itself.
- `normalize.age()`'s range detection required a lead verb ("aged", "matured"); a bare range with none
  ("4 - 6 Years Old") was falling through to the single-number pattern and returning the upper bound as
  if it were a specific age. Fixed to recognize a bare "N - N years" too. Re-verify every applied
  source's dry run after touching `normalize.py`, the same as for a `spirit_type()` change.
- A page that lists the current release then its full batch history in one page (Barrell's Batch
  Bourbon/Rye, New Year, Gold/Gray Label) has no toggle worth parsing — the current one is simply
  whichever text comes before the *second* mention of "N proof" (a single-release page never has one).
  A blend's own component list ("Kentucky: 12 years old", "Indiana: 5, 6, & 10 years old") states each
  component's age, not the batch's; strip that whole span before age-matching or the first number in
  the list reads as the batch's own age.
- A page that states no proof/age/mash anywhere is still worth crawling if the family's other pages
  are crawled: leaving it out doesn't skip it, it makes the importer think the maker stopped selling it
  and mark it discontinued (the dry run's STALE list is scoped to "a family the site covers"). Crawl it,
  let it parse to a proof-less record, and it confirms itself still-live instead (Barrell's Seagrass,
  Dovetail, Vantage, Armida, Private Release and its Cask Finish Series landing page all do this).
- `expression_key()`'s own boilerplate list strips the word "bourbon" (usually redundant — "10 Year
  Bourbon" ~ "10 Year"), so a maker whose product is *named* "Bourbon" outright (Barrell's Batch Bourbon,
  next to its blank-expression flagship blend) collides with the flagship's blank key and silently loses
  the match in `_dedupe()` before diffing ever runs — no error, the record just vanishes. Give it a
  distinguishing expression instead ("Batch Bourbon", the site's own nav term) and alias the old bare
  name so the existing row still matches by name.
- Two more real bugs, both narrow but both in shared `normalize.py` code, found by Barrell and
  re-verified clean across all 20 previously-applied sources: `mash_style()`'s rye/corn percentage regex
  only recognized "21% rye" order, not a maker who labels it "Rye: 21%"; and `finish()`'s "___ finish"
  pattern mistook a product LINE's own name ("Cask Finish Series") for a real cask-finish descriptor —
  a real single bottling never calls its own finish a "series".

## Phase 2 — TTB COLA as the second source (Q1 2027)

The COLA public registry holds every approved label: brand, class/type, proof, age statement,
bottler. It settles rows whose maker publishes no facts, proof on pages that only say "barrel
proof", and craft brands with no real site. It is a search form, not a crawlable site, so it is a
per-brand lookup module, not a crawl. Scoped after Tier 1 ships.

## Quarterly (folds into REVIEW.md)

1. Re-crawl every bourbon source; dry-run each. Corrections: read every one. Additions: the new
   bottlings; a Tier-1 maker's go live, others stay hidden drafts. Stale: pass only rows genuinely
   gone to `--stale-only`.
2. Apply; every matched row is stamped `source_checked_at` (freshness).
3. Promotion pass: hidden rows that gained a maker match and `is_core_range` → `catalog_included`.
4. Audit sample: 25 confirmed + 25 unconfirmed rows against the maker's page (or the bottle in hand).
5. Scorecard history row; pick next quarter's 3–5 importers from `targets.yml`.

## Decisions

- Breaking Bourbon stays a *review* source (`product_reviews`, wheel vectors). It stops being the
  facts source for any row a maker's page covers. The scorecard already says review and retailer
  data never count as confirmed.
- Completeness for bourbon stays proof + spirit type + producer + image. Rarity and mash style are
  wanted on every row but are not part of the bar; makers rarely state either.
- The bourbon importers live here, next to the cigar sources: one fetcher, one scorecard, one
  review runbook. `cellar/catalog/breakingbourbon` is the record of the September import, not a
  pipeline.
