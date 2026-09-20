# Catalog Confidence Scorecard

What "first in class" means for the Cellar catalog, in numbers. The view `cellar.catalog_scorecard`
computes every figure below from live rows (not merged, catalog-included, not discontinued):

```sql
select * from cellar.catalog_scorecard order by type;
```

## The north star

**Confirmed & complete** — the share of live rows whose facts come from the maker's own page
*and* that carry every fact a product card needs. A row counts only if both are true.

- *Confirmed*: `source = 'maker'` with a `source_url` on the maker's site (or, for bourbon, the
  distillery / TTB COLA record). AI, seed and retailer data never count.
- *Complete* (cigar): length, ring gauge, size name, wrapper leaf (not unknown/other), binder,
  filler, country, image. Body is deliberately excluded — most makers don't state it.
- *Complete* (bourbon): proof, spirit type, producer, image.

| | Baseline (2026-09-20) | Q4 2026 | Q1 2027 | Q2 2027 | Q3 2027 |
|---|---|---|---|---|---|
| Cigars confirmed & complete | **33%** (383 / 1,153) | 55% | 65% | 75% | **85%** |
| Bourbon confirmed & complete | **0%** (0 / 307) | 30% | 50% | 65% | **80%** |

## Supporting metrics

| Metric | What it measures | Cigar baseline | Target |
|---|---|---|---|
| Provenance | live rows confirmed by the maker | 40.7% (469) | ≥ 90% |
| Completeness | live rows with every card fact | 68.5% (790) | ≥ 95% |
| Brand coverage | brands with ≥ 1 confirmed row / brands in catalog | 19 / 122 | Tier 1 in `targets.yml` 100%, Tier 2 ≥ 80% |
| Line coverage | (brand, line) pairs with ≥ 1 confirmed row | 121 / 689 | ≥ 85% |
| Freshness | confirmed rows re-checked against the maker within 120 days | 100% | ≥ 90% at every quarterly review |
| Audit accuracy | hand-checked rows found correct (see REVIEW.md) | not yet run | ≥ 98% of sample, 0 errors in confirmed rows |
| Maker pages | distinct maker pages behind confirmed rows | 129 pages, 6 sites | input metric, no target |

Bourbon baseline: 307 live rows, 72.3% complete, 0% confirmed (184 rows carry a `source_url` but were
entered as `seed`; re-sourcing them from distillery pages / TTB COLA is the bourbon track).

## How the numbers move

- An importer run moves *provenance* (matched + added rows) and *freshness* (every matched row is
  stamped `source_checked_at`, changed or not).
- *Completeness* moves when the maker states a fact we lacked, or Paul fills one in-app. Makers rarely
  state body; the in-app editor is the path for that field and it is not in the completeness bar.
- *Brand coverage* moves one importer at a time. `targets.yml` is the queue.
- *Audit accuracy* is the only metric a person produces; it is what lets us say "confirmed" with a
  straight face. See REVIEW.md.

## History

| Date | Rows | Confirmed | Complete | Confirmed & complete | Brands confirmed | Notes |
|---|---|---|---|---|---|---|
| 2026-09-20 | 1,153 | 40.7% | 68.5% | 33.2% | 19 / 122 | Baseline after Drew Estate, Kristoff, Mayflower, Oliva, Nub, Hoyo de Monterrey. Punch / Cohiba / CAO applying. |
