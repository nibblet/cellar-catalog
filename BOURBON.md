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
Wagon, Barrell, Starlight, Rabbit Hole, Garrison Brothers, Castle & Key, Green River, Heaven's Door,
Chicken Cock, Yellowstone done 2026-09-25 — **Tier 2 queue complete**. Peerless, Wilderness Trail, Old
Elk remain blocked (no machine-readable spec data). Next: pick 3–5 new Tier 2/3 producers from the
catalog's own brand list (ranked by presence, same method `targets.yml`'s header describes), or start
Phase 2 (TTB COLA) below.

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
- A page that ends every product with a carousel of *other* products ("Explore More Spirits") means the
  first "N Proof" or "___ Whiskey" match on the page can belong to a sibling, not the bottling itself —
  Starlight's Blackberry and Peach Whiskey pages both false-matched "Bourbon Whiskey" this way before the
  carousel was truncated off first. Always cut the page down to its own content before pattern-matching
  anything, not just proof.
- A finishing or specialty SKU's own name often states nothing about what's in the bottle ("Mizunara
  Reserve", "Cigar Batch" name neither bourbon nor rye) — read the spirit class from the body copy's
  opening sentence instead of the name, and don't assume a shared URL bucket is a single spirit type
  (Starlight's `/finishings/orchard-blossom` is a Rye living among five Bourbon finishes).
- Boilerplate can restate a legal minimum verbatim across unrelated products: Starlight's "aged for a
  minimum of 4 years" appears on both its Bottled-in-Bond bourbon (legally exactly 4) and its plain Carl
  T. (not bonded, no reason to share the same floor) — the same lesson as "a law's minimum is not an
  age" applied to marketing copy that quietly reuses the law's own phrasing as a generic description.
  Strip the qualified phrase before reading age; an unqualified statement ("aged slowly for a full
  decade") on the same page is unaffected.
- A messy pre-existing seed under one old naming convention needs the same triage as any batch-row
  duplicate, just at a larger scale: Starlight's 24 seed rows split into rows that merge by an exact
  proof match, rows renamed in place where the current page now states no proof but the name is
  distinctive enough to be certain, and rows with no current-site correspondence at all (one-off
  single-barrel picks, retired cask finishes) that are simply discontinued. Don't guess a merge from
  name similarity alone when a proof or a distinctive term isn't there to anchor it.
- A brand's marketing domain can *be* its Shopify store rather than link to a separate one (Rabbit
  Hole's shop subdomain redirects back to the main site) — crawl each product's own `.json` endpoint
  directly (`SITEMAP` points at `/collections/all/products.json`) rather than scraping rendered HTML;
  `body_html` carries the same accordion copy the page shows, paginated `&page=N` when a collection
  holds more than the API's per-page cap.
- A Shopify store's own `product_type` field is not a scope filter: Rabbit Hole tags Bespoke Gin and
  Liddel Vodka as `"Whiskey"` alongside every real bourbon and rye. Scope from the source module's own
  REFILE table, never from the platform's own categorization.
- An alias must carry the family prefix the same as `name` does, not just the bare expression: pairing
  `expression="Boxergrail"` with alias `"Boxergrail Rye"` (instead of `"Rabbit Hole Boxergrail Rye"`)
  silently failed the name-match pass against the seed row of that exact title and would have inserted
  a duplicate rather than correcting and renaming it — caught by reviewing the dry run's ADDITIONS
  before writing SQL, not by any error.
- Two whiskeys aged in casks of very different sizes with no aggregate figure ("Barrel 1: 4+ Yrs /
  Barrel 2: 4 Mos") state no single age — `normalize.age()` already returns none for text shaped this
  way (the "+" breaks its numeric patterns), but the real lesson is not to add a special case to force
  a number out of it; a genuinely blended, unequal-age whiskey has no one age to report.
- A maker can state age as two sequential stages with no single sentence adding them ("spent four years
  in white American oak and four more in Pedro Ximénez sherry casks", "aged four years ... and aged an
  additional year") — `normalize.age()` only ever returns the first number it finds. Garrison Brothers'
  `_years()` sums every explicit "N years" mention, treats a bare "N more" as another mention of the
  established unit (not a fresh, unrelated one), and treats an unquantified "an additional year" as +1;
  this is deliberately its own module-local helper, not a `normalize.py` change, because the elliptical
  phrasing is this one maker's writing style, not a general pattern.
- A structured-data field can be stale on a page nothing else has changed on: Garrison Brothers' schema
  said Cowboy Bourbon was 146.4 proof while this year's body copy said 141.0 — an annually-updated
  release's *body text* is what changes each vintage, so read proof from there first and treat the
  page's own JSON-LD as a fallback only, not the source of truth, whenever both exist.
- A schema field can be a fixed site-wide default masquerading as a per-product fact: every Garrison
  Brothers product's JSON-LD `category` reads "Texas Straight Bourbon Whiskey" verbatim, including ones
  that would plausibly differ if the field were real. Sanity-check a structured field by comparing it
  across several pages before trusting it; `isRelatedTo` ("Permanent Collection" / "Limited Release")
  passed that check by matching the site's own separate "Our Babies" / "Limited Releases" nav split.
- A Shopify store's `.json` product API is not always the whole page: Castle & Key's `body_html` carries
  the marketing description and its "Aged for N years" statement, but proof and mash bill live only in
  the rendered page's theme-built "Tasting Notes" accordion, never in the JSON payload at all — crawl
  the rendered HTML when a fact the JSON promises turns out to live in the theme instead.
- A mash bill printed in abbreviated codes with no on-site legend (Castle & Key's "73% WC, 10% R, 17%
  MB") still needs expanding to spelled-out grain words before `normalize.mash_style()` can read it (it
  only recognizes "corn"/"rye"/"wheat"/"malted barley", never a maker's own shorthand) — infer the
  legend from standard bourbon/rye convention (WC/YC both corn, R rye, W wheat, MB malted barley) and
  say so as inference, not as something the site states.
- A release can name neither bourbon nor rye in its own title (Castle & Key's Experimental Series
  "Hungarian Tokaji Casks") when the base spirit isn't part of the marketing name at all; read the class
  from the description's own opening self-statement ("Our Rye is...", "Our Wheated Bourbon is...")
  rather than assuming a default, and watch for the OTHER type's name appearing incidentally in that
  same description (the wheated bourbon's own copy says "where rye would be" as a comparison).
- A distillery site's real age statement can live on a separate FAQ page, not the product's own page
  (Green River's flagship three state a fact like "aged more than five years" only there) — that page is
  not read as the bottling's own statement; if the product page itself states no age, the row's existing
  age stays untouched rather than being filled from a page a step removed from the product.
- "Aging" (present participle) is not "aged": Green River's "After aging eight years in the distillery's
  signature clay tile rickhouses" doesn't match any of `normalize.age()`'s "aged ..." patterns. A plain
  text substitution (`aging` → `aged`) before calling it is enough when a maker's copy uses the -ing form.
- A distiller can also be a contract supplier to other brands filed under their own family entirely
  (Green River bottles for Bradshaw, Walker's Cay and New England Barrel Company, each its own
  brand_family with `producer = 'Green River'`) — an importer scoped to the distiller's own site never
  touches those rows, since family is what diff.py matches on, not producer.
- A brand can fully rebrand its lineup (Heaven's Door: every core expression now carries a mythic release
  name — Refuge, Revival, Ascension, Revelation — over its old plain descriptive class) after the seed
  was written under the old names. Keep the old descriptive expression in `REFILE` and alias the new
  release name (or vice versa, whichever the seed already used) rather than adopting the new marketing
  name outright — the point is matching the existing row, not chasing the current brand voice.
- The Barrell "bare Bourbon collides with the flagship's blank expression" bug recurs anywhere a state or
  region name sits next to the word "Bourbon": Heaven's Door's "Kentucky Bourbon" and "Tennessee Bourbon"
  both strip to an empty `expression_key()` (`kentucky`, `tennessee` and `bourbon` are all in the
  boilerplate list) and collided in `_dedupe()` exactly like before, silently dropping one before
  matching ever ran. Renaming to "KY Straight Bourbon" / "TN Straight Bourbon" survives stripping via the
  untouched abbreviation. Whenever an expression is built from state/region + "Bourbon" alone, check its
  `expression_key()` isn't empty before trusting the dry run's silence about it.
- A collection/series landing page can be genuinely live (200, linked from nav, not a dead redirect) while
  still stating no proof anywhere in static text for its individual numbered releases (Heaven's Door's
  Bootleg Series, Decade Series, Exploration Series, Master Blender's Edition) — this is a different case
  from a page that's actually gone (Green River's vanished "U.S. Army 250th Anniversary"). Don't mark a
  seed row discontinued just because it wasn't crawled; that claims the maker no longer lists it, which a
  live-but-data-poor landing page doesn't support. Leave it as seed and say why in the write-up.
- A host's WAF can specifically flag a *spoofed* browser User-Agent while accepting a plain or custom one
  (Chicken Cock: a desktop-Chrome UA string gets 403, `curl`'s default, a bare "Mozilla/5.0", and a custom
  identifying string all get 200) — the heuristic is "browser-claiming but non-browser-behaving," not
  bot-blocking outright. `catalog/fetch.py`'s own UA already identifies itself rather than impersonating a
  browser, so this needs no workaround, but it's a reason never to reach for UA-spoofing as a first fix
  when a fetch fails; try the project's own honest UA before assuming a real bot wall.
- A brand's newest releases can predate its own current page layout: Chicken Cock's structured
  PROOF:/AGE:/MASHBILL: block only exists on the newer core lineup: older limited releases (Chanticleer,
  the 15 Year, 20 Year Cotton Club Rye) still state proof only in inline prose and give no age field at
  all. When a product's own name states its age plainly ("15-year-...", "20-year-old-...") and the page
  doesn't, reading it from the slug or title is not a guess — it's the same fact the maker put in the URL.
- A sold-out bottling ("Bottles Remaining | 0") is still the maker's current, standing statement of that
  bottling's specs — proof/age/mash bill don't stop being confirmed facts just because the product can no
  longer be bought; only a page that's gone entirely is grounds for treating a row as no longer listed.
- A page can flatly contradict itself: Yellowstone's Single Barrel states "Bottled-in-Bond" (legally
  exactly 100 proof) while displaying "93 Proof" a paragraph later — clearly copy-pasted from a sibling
  page. The label's own legal claim (BiB, a federal definition) wins over its own displayed number, the
  same call made for Barton 1792's Full Proof; don't average or split the difference between two
  contradictory maker statements when one of them is independently verifiable by law.
- An elliptical component-age list ("a perfect blend of 4- and 7-year bourbons") states two ages with no
  aggregate, but the ellipsis ("4-" with "year" only attached to the second number) means a naive
  extraction only ever finds the *second* number and reports it as if it were the whole story — worse
  than finding neither, since it looks like a real answer. Strip the whole "N- and N-year" span before
  calling `age()` rather than trust whichever half survives the parse.
- `og:image` can be a fixed site-wide default (Yellowstone's is the same logo on every single product
  page) even when the page has a real, distinct bottle photo elsewhere in the DOM — check that an
  og:image actually varies page to page before trusting it; when it doesn't, find the maker's own image
  folder convention instead (`imgs/bottles/<name>` here) and take the first match.
- An annually-overwritten page can have a same-year dated mirror URL that means nothing archivally
  (Yellowstone's `/limited-edition-25/` duplicates `/limited-edition/` for the current cycle only; every
  guessed past year's URL 404s) — don't infer a historical-batch-archive pattern from one dated URL
  existing; check whether prior years' guesses actually resolve before assuming the pattern is real.

- A "parked, no numbers" verdict has a shelf life, and the number may sit on a page that isn't a
  product page. Old Elk's Squarespace site was rebuilt and now prints the proof under every bottling;
  Wilderness Trail's three product pages never did, but its FAQ, process and whiskeys pages state
  "bottled in bond ... exactly 100 proof" for the lineup it names. A module may read such a brand-wide
  sentence at parse time and degrade to "no proof" if it disappears. Grep every nav page before parking.
- A site's own domain can be a shell while a sibling host on the maker's domain or the brand owner's
  shop is the real maker page (IJW's `ijwwhiskey.com` vs Puncher's Chance on `ourwolfspirit.com`;
  highwest.com's empty Shopify vs `ship.highwest.com`). State the substitution in the module docstring.
  Conversely a brand's official domain can lapse and be re-registered by an unrelated site (Kentucky
  Owl): check the page's title and body, not just the 200.
- Squarespace and Duda sites keep stale slugs, sitemap entries and footer links. The nav is the list and
  the page heading names the bottling (Four Gate's `batch-30-triple-oak` is Batch 29); map from the
  heading, never the slug.
- Numbers on a product page can belong to someone else: carousels ("Try These Next", "Explore More",
  "FIND NEAR ME" tails), testimonials, shared disclaimers naming another bottling, a second spec block
  left over from the previous batch (take the first), and component ages in a blend ("5- and 6-year-old",
  "5 years 10 months", age at re-barreling). Read age only from an `Age:` field, the title, or the
  opening blurb, and never from the Bottled-in-Bond explainer's "four years" floor.
- A page can carry several bottlings (Blue Run's Flight Series III, Four Gate's Bluegrass Trilogy,
  High West's limited-releases page): return a list from `parse()`. Conversely a producer that names
  every annual vintage after something (Pinhook's racehorses) gives each its own page: fold same-title
  vintages into one record, oldest first so the newest wins, and merge the old per-vintage rows.
- A blend of the same straight whiskey is that whiskey: High West's Double Rye is rye, not `blend`;
  reserve `blend` for cross-type blends (Campfire, Bourye). A component statement or a finishing
  subtitle in `class_raw` can poison `spirit_type()` ("blend of straight bourbons", "finished in rum
  cask solera"): build `class_raw` from the label class and carry the finish separately.
- `normalize.mash_style()` reads "20.5% rye" as "5% rye" (its percentage pattern takes no decimals), so a
  20.5%-rye bourbon reads traditional. Pinhook computes the style in-module; the narrow fix to
  `normalize.py` is still open (see the round's hand-off), then re-verify every applied source.
- `normalize.finish()` false-positives on prose ("no matter the barrel finish we choose", "a distinct
  secondary cask"): modules that see this read the finish themselves.
- The writer used to promote only seed rows that already had `is_core_range`; it now also sets it from
  the module's CORE table on a match. Rows matched by earlier runs were not backfilled, so check
  `source = 'maker' and not catalog_included` after a run. The `discontinued` update now carries the
  `facts_verified_at is null` guard, and `export.py` carries `specs.source_image_url` so a stored image
  address stops reading as a pending "image: site has one" correction.
- A `Crawl-delay` in robots.txt is a floor on politeness, not a hint (Oregon Spirit: 30; Clyde May's,
  Old Elk: 10): set the module's DELAY to it.
- A seed placeholder named only for the brand can be a specific release (Puncher's Chance = The Left
  Cross; Oregon Spirit = the 2017 BiB bourbon). Identify it from its own curated specs and age/proof
  before merging; never from name similarity.

- A bottle's label is the maker's own legal statement of proof, and many sites state it only inside the bottle
  photo (Stellum, Two Times Oak's American Oak). When the text has no number, read the full-size photo of the
  maker's own page (not a retailer's), record each reading and the image id in the module, and use it only while
  that same image is still on the cached page. Cross-check against the seeded values: Stellum's six readings landed
  within 0.06 of the seeds. Lifestyle shots with a label too small to read confirm nothing.
- A host that blocks the importer's honest client (Cloudflare 403) is not bypassed, but the pages can still be read
  by a person-paced browser session. Only with the owner's explicit approval, and recorded as such: save the
  main-content text into the module's cache (Jefferson's, `cache/jef`) and commit those files, since `cache/` is
  git-ignored and they are the evidence. A re-read means refreshing them by hand; never script it.
- A site that "states no proof" can change (Jefferson's rebuilt site now says "bottled at 88 proof" in prose):
  re-check parked makers on a schedule, and grep every nav page for "proof" before parking.
- A short marketing page can carry its only proof in its slug or image file name (Bluegrass' `100-proof-mash-bill-1`),
  and a shared series blurb ("barrel-aged at least 3 years") is not a bottling's age. Each of A. Smith Bowman's
  pages repeats its proof block once and the repeat can be an older copy: read the first block.
- A seeded age with no maker statement is a candidate for NAS, not a fact to keep (Abraham Bowman releases carried
  their release numbers as ages): the owner cleared four such rows on 2026-10-11 (`sql/20261011_bowman_jefferson_ages.sql`).
- The writer now fills a null `rarity` on matched/corrected rows from the module's `RARITY` table (never overwrites a
  set one). The 2026-10-11 backfill (`scripts/bourbon_promote.py`, `sql/20261011_rarity_and_core_backfill.sql`) applied
  that to rows matched by earlier runs and promoted 67 core rows; maker rows still hidden are the ones their modules
  call non-core (limited, anniversary, experimental), on purpose.

- A single-page app can hide its whole catalogue in one public JS bundle (Fireside's drinkmhs.com: every URL serves
  the same empty shell, the products are a literal array in `/assets/index-<hash>.js`): crawl the home page for the
  bundle name, then the bundle, and parse the array. Check for this before concluding "no machine-readable data".
- Two page families can describe one bottle (WhistlePig's `/whiskeys/` and `/product/`; Lucky Seven's collection and
  store pages): pick the complete one or merge them in module state, since the diff keeps the last record per bottling.
- `key()` cuts at "(" and `expression_key()` drops digits, so "X (5 Year)", "X (7 Year)" and "X (8 Years)" collide and the
  matcher cannot claim a specific one: add the maker's row and merge the exact-match child with `cellar.merge_product`.
- Twins with one `expression_key` ("Honey Cask Rye" / "Honey Rye Cask") and a unique index on (family, expression,
  release_label) mean a writer rename can hit a live twin: merge twins first, then run the writer.
- A seeded age the maker contradicts or never states survives the writer (it only fills an empty age): the dry run does
  not list it, so list those by hand (H.K. Young's blend, Town Branch's flagship, Horse Soldier's flagship, Shortbarrel
  Four Grain) for an owner NAS/clear decision.
- Matched rows keep `status = 'draft'` even when the writer sets `source = 'maker'` (264 rows on 2026-10-12): the
  scorecard and the app don't read it, but check the catalog-management UI before deciding whether the writer should
  also set `status = 'confirmed'`.
- A brand that is only a label (O.K.I., Blackened) has no maker site: its domain 301s to a social page or a retailer, or
  sits parked. Check redirects without `-L`, report it blocked, and settle it through TTB COLA (Phase 2).
- A brand's own-name domain can be a different business entirely (townbranch.com is an apartment complex): follow the
  old domain's redirect and check the page content.

## Owner decisions (2026-10-12)
Applied (`sql/20261012_owner_decisions.sql`): nine seeded ages the maker never states cleared to NAS (H.K. Young Toasted Barrel
Blend, Horse Soldier, Shortbarrel Four Grain, Town Branch, Hard Truth Four Grain and Wheated, Blue Note Special Reserve and the two
Honey casks); the two Eighteen33 rows flagged discontinued; Town Branch Reserve Rye merged into Single Barrel Reserve Rye; O.K.I.
producer and maker now OKI Spirits LLC; Fireside Single Barrel (4 yr) no longer core.

Still open: Hard Truth's other seeded ages the maker never states (Chocolate, Caramel and Malted Rye 2, French Oak Harvest Rye 3,
Double Oaked Sweet Mash Rye 5, Maple Brulee 4, the flagship 'Hard Truth' 14); the Peerless Straight Bourbon (109.8) vs Small Batch
Barrel Proof (109.5) pair; whether the writer should also set `status = 'confirmed'` on maker rows (264 still 'draft'; check the
catalog-management UI first); WhistlePig Beyond Bonded Bourbon (BiB, no proof printed — read as 100?); ~134 non-core maker rows
stay hidden on purpose.

## Phase 2 — TTB COLA as the second source (Q1 2027)

The COLA public registry holds every approved label: brand, class/type, proof, age statement,
bottler. It settles rows whose maker publishes no facts, proof on pages that only say "barrel
proof", and craft brands with no real site. It is a search form, not a crawlable site, so it is a
per-brand lookup module, not a crawl. Scoped after Tier 1 ships.

## Continuing the catalog (after the 2026-10-11 round)

Order of work, each cheap relative to the last:

1. **Demand first.** Rank the unconfirmed seed families by member saves, then row count
   (`cellar.member_saves` joined to `cellar.products where source <> 'maker'`). On 2026-10-11 the top of that list was
   Shortbarrel (4 saves), WhistlePig, RD One, Hard Truth (24 rows), Blue Note, Lucky Seven, Town Branch, Blackened,
   O.K.I., Horse Soldier, H.K. Young, Boone County. Run those through the importer pipeline in parallel batches of
   1-3 makers per agent (module + cache + SQL file each; the coordinator owns shared docs and the commit).
2. **Family hygiene** before more rows: one brand under two families ("Bluegrass" / "Bluegrass Distillers",
   "Peerless" / "Kentucky Peerless", "James B. Beam"), wrong producers (Benchmark filed under A. Smith Bowman), and
   one-off seed rows that belong to a release. These need `cellar.merge_product` or a producer fix, not importers.
3. **Parked makers on a clock.** Re-check blocked/parked makers every quarter: Old Elk and Wilderness Trail unparked on
   re-read, Jefferson's turned out to state proof. Still parked: Smooth Ambler, Driftless Glen, Legent, Peerless,
   Kentucky Owl (no maker site). These, and anything with no proof in text, are the case for Phase 2 (TTB COLA).
4. **New producers, quarterly.** Scan for new DSPs and newly launched brands (state distillers' guild lists, TTB
   permit changes, new-release coverage), add the ones with a real site to `targets.yml`, and triage into step 1.
5. **Refresh and review of active makers.** Re-crawl the done makers on a rolling schedule (use `source_checked_at`
   to find the stalest), read every dry-run correction, and run the 25 + 25 audit sample. Drift to look for: proof
   changes (Pinhook, Breckenridge), renamed or retired bottlings, seeded ages the maker never states.

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
