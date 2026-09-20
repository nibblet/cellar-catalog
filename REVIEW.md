# Quarterly catalog review

Runs in the first two weeks of January, April, July and October. Takes an afternoon of machine
time and about two hours of Paul's. The output is one new row in SCORECARD.md's history table
and a short note of what changed.

## 1. Re-crawl every source (machine)

Caches live in a scratch directory and are not kept between quarters, so each review fetches
fresh. Delays are per source and polite; the whole set runs in the background in under an hour.

```bash
for s in drew_estate kristoff mayflower oliva nub hoyo punch cohiba cao; do
  python3 scripts/crawl.py $s cache/$s
done
```

## 2. Export and dry-run each source (machine)

Export the brand's current rows (`scripts/dry_run.py`'s docstring has the query — export *all*
of the brand's rows) and run the dry run. Read every section:

- **Corrections** — a maker changed a fact, or a fact we had was wrong. Expect few; read each.
- **Additions** — new sizes and lines since last quarter. Skim for parse noise (a size named
  after a promo, a sampler that slipped past the skip list).
- **Stale** — rows the maker no longer lists. This is the discontinuation signal. Pass only the
  rows that are genuinely gone to `--stale-only`; a maker's site is not always exhaustive.
- **Placeholders / overrides** — rows that need a human decision go into the source's `OVERRIDES`.

## 3. Apply (machine, Paul approves each source)

`scripts/write.py` emits `part1.sql` and insert batches. Apply in order. Every matched row is
stamped `source_checked_at`, which is what keeps freshness at 100% for that source.

## 4. Audit sample (Paul, ~1 hour)

Fifty rows, chosen at random, checked by eye against the maker's page in the in-app editor:

```sql
(select id, name, brand, source_url from cellar.products
   where type = 'cigar' and source = 'maker' and merged_into is null and facts_verified_at is null
   order by random() limit 25)
union all
(select id, name, brand, source_url from cellar.products
   where type = 'cigar' and source <> 'maker' and merged_into is null and facts_verified_at is null
   order by random() limit 25);
```

For each row: open the source page (or search the maker's site for non-confirmed rows), compare
size, wrapper, binder, filler, body, country. Correct in-app if wrong, then mark verified. Record
`errors / 50` split by confirmed vs not. A confirmed-row error is a parser bug: file it, fix the
source module, re-run that source.

## 5. Read the scorecard, add the history row (machine + Paul)

```sql
select * from cellar.catalog_scorecard order by type;
```

Append the row to SCORECARD.md. If a target was missed, the note says why and what changes next
quarter (usually: which importer to build, or which field the makers don't publish).

## 6. Pick next quarter's importers (Paul)

From `targets.yml`: the highest-tier brands still `todo`, three to five of them, favouring makers
whose sites publish sizes as text. Flip them to `next`. Anything found `blocked` (age gates, bot
walls, sizes only in images) gets a note so nobody re-discovers it.

## 7. Housekeeping (machine)

- `makers` duplicates: `select name, count(*) … group by lower(regexp_replace(name, '\W', '', 'g'))`.
- Rows still `wrapper_leaf = 'other'` or with `expression is null` on a line the maker lists.
- Discontinued rows older than two years with no inventory or reviews referencing them can be
  hidden from search (`catalog_included = false`); nothing is ever deleted.

## Bourbon track

Same shape, different source: distillery product pages where they exist, and TTB COLA records for
proof and class/type. Confirmed for bourbon means `source_url` points at one of those. Until that
importer exists, the bourbon audit sample is 25 rows against the bottle in hand.
