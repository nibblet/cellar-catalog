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
| Diageo | bulleit.com, georgedickel.com, bladeandbowwhiskey.com | Bulleit, George Dickel, Blade and Bow, I.W. Harper |
| Lux Row / MGP | luxrowdistillers.com, rebelbourbon.com | Rebel, Ezra Brooks, Old Ezra, Daviess County, Blood Oath |
| Michter's | michters.com | Michter's |
| Angel's Envy (Bacardi) | angelsenvy.com | Angel's Envy |
| Jefferson's | jeffersonsbourbon.com | Jefferson's |

Tier 2 (Q1 2027): Willett, New Riff, Bardstown Bourbon Co, Wilderness Trail, Penelope, Smoke
Wagon, Old Elk, Barrell, Starlight, Peerless, Widow Jane, Uncle Nearest, Garrison Brothers, Rabbit
Hole, Castle & Key, Green River, Chicken Cock, Heaven's Door, Yellowstone.

The queue lives in `targets.yml` under `bourbon:`.

### What a maker's page gives that a review can't

Current proof and age (a review is frozen at its date; Elijah Craig's 12 sat in the catalog for
nine years after the label dropped it), a bottle shot for every row (102 live rows had none),
and discontinuation — a bottling gone from the maker's page is the stale signal, the same as a
cigar line gone from its site.

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
