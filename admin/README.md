# Catalog admin

A local review-and-edit UI for `cellar.products`, for the work the importers can't do: single-row
fixes, the quarterly audit sample (REVIEW.md step 4), and the housekeeping queues. Bulk changes
still go through the importers; this tool never deletes anything.

```bash
cd admin
cp .env.example .env.local     # once; the publishable key is safe to ship
npm install                    # once
npm run dev                    # http://localhost:5173
```

Sign in with an admin email (magic link). Writes go through row-level security as you, so the app
can do exactly what `cellar.is_admin()` allows and nothing else; there is no service key.
One-time Supabase setting: Authentication → URL Configuration → Redirect URLs must include
`http://localhost:5173/**`, or the link lands on the site URL instead.

## What's in it

- **Header**: the live `catalog_scorecard` figures for the selected type, each against its target
  in SCORECARD.md (read from that file at load, so edit targets there). The headline shows the next
  quarterly target not yet met and how many rows it needs; hover it for every quarter. Supporting
  metrics show their ≥ target and what's left to go; audit accuracy comes from `cellar.audit_checks`.
- **Queues**: From maker, missing facts (the fastest way to move the north star), Not from maker
  and Incomplete (ordered by `targets.yml` tier), Audit sample, Placeholders, Wrapper "other", Stale
  source check, Drafts, Recently edited, Re-filed, and two reference lists: Not hand-checked and
  Out of catalog. A queue is frozen while you work it, so a fixed row stays put; click the queue
  again to re-evaluate.
- **Terms**: *from maker* (confirmed) means an importer took the facts from the maker's own page;
  *complete* means every card fact is filled; *hand-checked* (verified) means an admin signed off,
  which also locks the row against importer updates.
- **Editor**: every card fact, provenance, verify / unverify, discontinued, hide, merge (through
  `cellar.admin_merge_product`, which moves member saves, tastings, reviews and images), and the
  row's change history.

## Rules it follows

- **Verification.** Saving a fact change on a verified row re-stamps `facts_verified_at`, because
  `cellar.protect_verified_facts()` refuses the change otherwise. Verified rows are never
  overwritten by importers, so verify only what you've checked against the maker.
- **Re-filing.** Changing a maker row's brand, line or size name puts it in the Re-filed queue with
  the `OVERRIDES` entry to paste into its source module, so the next crawl agrees.
- **Audit.** In the Audit sample, *Correct* records the check and verifies the row; *Was wrong*
  saves your fix, verifies, and records the error. A wrong confirmed row is a parser bug (REVIEW.md).
- **History.** `cellar.product_edits` is filled by trigger for every writer; importer SQL run in
  the SQL editor shows as "SQL / importer".

Keys: `j`/`k` move, `/` search, `e` edit, `o` open the maker page (reuses one tab), `v` verify,
`c` audit-correct, `⌘S` save, `⌘↵` save & verify, `esc` leave a field.

Backing SQL: `sql/20260924_catalog_admin.sql`.
