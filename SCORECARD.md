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
  distillery / TTB COLA record). AI, seed and retailer data never count. One documented exception:
  a maker that never states where a line is rolled may get its country from a curated per-line map
  in the source module (CAO, Davidoff group today), commented with its basis.
- *Complete* (cigar): length, ring gauge, size name, a wrapper (leaf named, or at least its
  origin — "Honduran Jamastran" is how some makers state it), binder, filler, country, image.
  Body is deliberately excluded — most makers don't state it.
- *Complete* (bourbon): proof, spirit type, producer, image.

| | Baseline (2026-09-20) | Q4 2026 | Q1 2027 | Q2 2027 | Q3 2027 |
|---|---|---|---|---|---|
| Cigars confirmed & complete | **33%** (383 / 1,153) | 55% ✓ (57.7% on 2026-09-20) | 65% | 75% | **85%** |
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
| 2026-09-20 | 1,153 | 40.7% | 68.5% | 33.2% | 19 / 122 | Baseline after Drew Estate, Kristoff, Mayflower, Oliva, Nub, Hoyo de Monterrey. |
| 2026-09-20 | 1,465 | 54.9% | 63.6% | 36.2% | 21 / 122 | Punch, Cohiba, CAO applied (+315 rows). Completeness fell: CAO's 163 new rows carry no country (General doesn't state it per line) and General names many wrappers by region only (205 rows unknown leaf). Both are the next completeness levers. |
| 2026-09-20 | 1,465 | 54.9% | 72.6% | 45.3% | 21 / 122 | CAO countries filled (3 lines from the maker's copy, the rest from the curated `COUNTRY_BY_LINE` map in `cao.py`); 8 General rows got a leaf from the page copy. 197 rows still have no leaf: 121 maker-sourced where the maker names only the region, 76 seed/AI rows awaiting their importer. |
| 2026-09-20 | 1,465 | 54.9% | 79.6% | 50.9% | 21 / 122 | Definition change: a wrapper known by origin alone now counts as complete (the maker's full statement for region-named leaves). 84 rows have no wrapper fact at all. |
| 2026-09-20 | 1,764 | 64.2% | 80.6% | 57.7% | 24 / 122 | Macanudo, Partagas, La Gloria Cubana applied (+299 rows; 335 maker pages). Q4 target met early. Parser now reads "Estelí-made", "crafted in Estelí" (accented) and "the El Credito Cigar Factory" as a country; the maker's copy overruled one curated-map entry (LGC Spanish Press is El Credito, not Estelí) — a reminder that the map is a fallback, not a source. 103 rows still lack any wrapper fact; Macanudo M / Emissary / Mao and LGC's one-off releases carry no country because General doesn't say. |
| 2026-09-20 | 1,843 | 67.2% | 81.7% | 60.8% | 25 / 122 | Padrón applied: 27 seed rows corrected (most had wrong dims), 79 added; 106 rows, one per wrapper. Country, wrapper, binder and filler cited from Padrón's company-wide Vertical Integration page rather than per-line copy — the one broad maker statement in the catalog so far. Diff no longer lets a name-derived parejo demote a stored figurado. |
| 2026-09-20 | 1,961 | 70.2% | 78.3% | 59.4% | 26 / 122 | Arturo Fuente applied: 21 seed rows corrected (dims wrong on most), 118 added; 139 rows, one per wrapper. Provenance up, confirmed & complete down a point: Fuente's pages state binder and filler only for OpusX, Casa Cuba and Especiales, so 94 confirmed rows are incomplete on the maker's own silence. Writer now confirms provenance on rows the maker agrees with outright (they used to stay `seed`). |
| 2026-09-20 | 2,125 | 73.8% | 79.7% | 63.2% | 31 / 123 | Davidoff group applied (Davidoff, Avo, Camacho, Zino, Zino Platinum): 26 seed rows corrected, 164 added, 8 makers → 1. The store's structured data names wrapper/binder/filler origins and an intensity for every product, so nearly all rows are complete; country from the approved per-brand map. Sizes filed twice by the store are deduped; release buckets (Limited Edition, Chefs Edition, Primeros) keep each product's own blend. Two 19-ring mini cigarillos fail the schema's ring check and were left out. |
| 2026-09-20 | 2,227 | 76.2% | 80.7% | 65.9% | 40 / 129 | My Father applied (My Father, Don Pepin Garcia, Flor de las Antillas, El Centurion, Jaime Garcia, La Dueña, La Antiguedad, Fonseca, Tabacos Baez): 20 seed rows corrected, 106 added, 4 seed duplicates merged, 7 makers → 1. The seed had filed the maker's other brands as My Father lines; they are re-filed as brands with the old names aliased. Country per page from the maker's copy: Don Pepin Garcia Original and Series JJ are "HandCrafted in the USA", My Father Blue and La Lealtad in Honduras, the rest Nicaragua — three seed rows had guessed Nicaragua and were overruled by the maker. Several wrappers are stated as "Sun Grown" only (no leaf, no origin) and stay unknown; "Sumatra" alone no longer implies Indonesia. |
| 2026-09-20 | 2,397 | 78.7% | 76.6% | 63.6% | 43 / 130 | Rocky Patel applied (Rocky Patel, Java, Nish Patel): 18 seed rows corrected, 170 added, 4 makers → 1. Confirmed up, confirmed & complete down two points: only 9 of 42 pages state the blend as fields, so wrapper comes from the page copy where it names a leaf (31 lines) and binder/filler only where the copy names them plainly — 11 lines have no wrapper at all. Country for every line from the maker's own Honduran / Nicaraguan collection pages, body from its mild / medium / full tiers. Eight pages (Conviction, Dark Star, Gold Label, Thirtieth Anniversary, Year of the Dragon…) list no sizes, so those rows stay seed. |
