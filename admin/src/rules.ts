// The scorecard's definitions (sql/20260920_catalog_scorecard.sql), REVIEW.md's queues and
// targets.yml's tiers, applied to rows already in memory.
import targetsYml from '../../targets.yml?raw'
import type { AuditCheck, Edit, Product, ProductType } from './types'

export const isLive = (r: Product) => !r.merged_into && r.catalog_included !== false && !r.discontinued
export const isConfirmed = (r: Product) => r.source === 'maker' && !!r.source_url

/** The facts a product card needs that this row lacks; empty = complete. */
export function missing(r: Product): string[] {
  const out: string[] = []
  if (r.type === 'cigar') {
    if (r.length_in == null) out.push('length')
    if (r.ring_gauge == null) out.push('ring')
    if (!r.expression) out.push('size name')
    if ((!r.wrapper_leaf || r.wrapper_leaf === 'unknown' || r.wrapper_leaf === 'other') && !r.wrapper_origin) out.push('wrapper')
    if (!r.binder) out.push('binder')
    if (!r.filler) out.push('filler')
    if (!r.country) out.push('country')
  } else {
    if (r.proof == null) out.push('proof')
    if (!r.spirit_type) out.push('spirit type')
    if (!r.producer_id) out.push('producer')
  }
  if (!r.image_url) out.push('image')
  return out
}

export function quarterOf(d = new Date()): string {
  return `${d.getFullYear()}-Q${Math.floor(d.getMonth() / 3) + 1}`
}

/** FNV-1a: a stable pseudo-random order, so the quarter's audit sample survives reloads. */
function hash(s: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193)
  return h >>> 0
}

// targets.yml: `- {brand: X, ... status: y}` under tier1/tier2, `- {producer: X, ...}` under bourbon.
export interface Target { tier: 1 | 2; status: string }
export const TARGETS: Map<string, Target> = (() => {
  const m = new Map<string, Target>()
  let tier: 1 | 2 = 1
  for (const line of targetsYml.split('\n')) {
    if (/^tier2:/.test(line)) tier = 2
    if (/^(tier1|bourbon):/.test(line)) tier = 1
    const name = line.match(/\{\s*(?:brand|producer):\s*([^,]+?)\s*,/)?.[1]
    const status = line.match(/status:\s*(\w+)/)?.[1] ?? 'todo'
    if (name) m.set(name.toLowerCase(), { tier, status })
  }
  return m
})()
export const targetOf = (r: Product) => TARGETS.get((r.brand ?? '').toLowerCase())

export interface Ctx {
  audits: AuditCheck[]      // this quarter's
  edits: Edit[]             // recent
}

export interface Queue {
  id: string
  label: string
  hint: string
  rows: (all: Product[], type: ProductType, ctx: Ctx) => Product[]
}

const ofType = (all: Product[], type: ProductType) => all.filter((r) => r.type === type)
const live = (all: Product[], type: ProductType) => ofType(all, type).filter(isLive)
const byTier = (a: Product, b: Product) =>
  (targetOf(a)?.tier ?? 9) - (targetOf(b)?.tier ?? 9) || (a.brand ?? '').localeCompare(b.brand ?? '') || a.name.localeCompare(b.name)

export const QUEUES: Queue[] = [
  { id: 'all', label: 'All live', hint: 'Every row in the catalog: not merged, included, not discontinued.',
    rows: (all, t) => live(all, t) },
  { id: 'audit', label: 'Audit sample', hint: 'REVIEW.md step 4: this quarter\'s random sample. Check each against the maker\'s page, then mark it correct or fix it.',
    rows: (all, t, ctx) => {
      const audited = new Set(ctx.audits.map((a) => a.product_id))
      const q = quarterOf()
      const pool = live(all, t)
        .filter((r) => !r.facts_verified_at || audited.has(r.id))
        .sort((a, b) => hash(a.id + q) - hash(b.id + q))
      if (t === 'bourbon') return pool.slice(0, 25)
      return [...pool.filter(isConfirmed).slice(0, 25), ...pool.filter((r) => !isConfirmed(r)).slice(0, 25)]
    } },
  { id: 'confirmed-incomplete', label: 'From maker, missing facts', hint: 'Importer rows (source = maker) missing a card fact. Open the maker page: if it states the fact, fill it in; if it never does, leave it. Each one completed moves the north star.',
    rows: (all, t) => live(all, t).filter((r) => isConfirmed(r) && missing(r).length > 0).sort(byTier) },
  { id: 'unconfirmed', label: 'Not from maker', hint: 'Facts from seed, AI, retailer or manual entry, not a maker page. Ordered by targets.yml tier: for T1 brands the fix is usually an importer.',
    rows: (all, t) => live(all, t).filter((r) => !isConfirmed(r)).sort(byTier) },
  { id: 'incomplete', label: 'Incomplete', hint: 'Any live row missing a card fact.',
    rows: (all, t) => live(all, t).filter((r) => missing(r).length > 0).sort(byTier) },
  { id: 'placeholders', label: 'Placeholders', hint: 'Line known, size not (expression is null). Report, don\'t guess.',
    rows: (all, t) => t === 'cigar' ? live(all, t).filter((r) => !r.expression) : [] },
  { id: 'wrapper-other', label: 'Wrapper "other"', hint: 'REVIEW.md housekeeping: wrapper_leaf = other usually means an origin was taken for a leaf.',
    rows: (all, t) => t === 'cigar' ? live(all, t).filter((r) => r.wrapper_leaf === 'other') : [] },
  { id: 'stale', label: 'Stale source check', hint: 'Confirmed rows not re-checked against the maker in 120 days.',
    rows: (all, t) => {
      const cutoff = Date.now() - 120 * 86_400_000
      return live(all, t).filter((r) => isConfirmed(r) && (!r.source_checked_at || Date.parse(r.source_checked_at) < cutoff))
    } },
  { id: 'drafts', label: 'Drafts', hint: 'status = draft among live rows.',
    rows: (all, t) => live(all, t).filter((r) => r.status === 'draft') },
  { id: 'edited', label: 'Recently edited', hint: 'Rows changed in the last 14 days, newest first (any writer).',
    rows: (all, t, ctx) => {
      const byId = new Map(all.map((r) => [r.id, r]))
      const seen = new Set<string>()
      const out: Product[] = []
      for (const e of ctx.edits) {
        const r = byId.get(e.product_id)
        if (r && r.type === t && !seen.has(r.id)) { seen.add(r.id); out.push(r) }
      }
      return out
    } },
  { id: 'refiled', label: 'Re-filed', hint: 'Maker rows whose brand, line or size name was changed by hand. Copy each into its source\'s OVERRIDES so the next crawl agrees.',
    rows: (all, t, ctx) => {
      const ids = new Set(ctx.edits.filter((e) => e.changed_by && refiled(e)).map((e) => e.product_id))
      return ofType(all, t).filter((r) => ids.has(r.id) && r.source === 'maker')
    } },
  { id: 'unverified', label: 'Not hand-checked', hint: 'Reference, not a to-do list: rows no one has signed off on (facts_verified_at). Hand-checking happens through the Audit sample. A verified row is locked against importer updates, so verify only what you have checked.',
    rows: (all, t) => live(all, t).filter((r) => !r.facts_verified_at).sort(byTier) },
  { id: 'out', label: 'Out of catalog', hint: 'Merged, hidden or discontinued. Nothing is deleted.',
    rows: (all, t) => ofType(all, t).filter((r) => !isLive(r)) },
]

export const refiled = (e: Edit) => ['brand', 'line', 'expression'].some((k) => k in e.after)

/** catalog/write.py _name(): line + size, dropping the words the size repeats. */
export function cigarName(line: string | null, size: string | null): string {
  if (!line || !size) return size || line || ''
  const l = line.toLowerCase(), s = size.toLowerCase()
  if (s.startsWith(l) || l.startsWith(s) || ` ${s} `.includes(` ${l} `)) return size
  const lw = line.split(/\s+/), sw = size.split(/\s+/)
  for (let n = Math.min(lw.length, sw.length); n > 0; n--) {
    if (lw.slice(-n).map((x) => x.toLowerCase()).join(' ') === sw.slice(0, n).map((x) => x.toLowerCase()).join(' ')) {
      return [...lw, ...sw.slice(n)].join(' ')
    }
  }
  return `${line} ${size}`
}

/** A Python literal for an OVERRIDES entry. */
const py = (v: unknown) => (v == null ? 'None' : JSON.stringify(v))
export function overridesEntry(r: Product): string {
  const parts = [`"brand": ${py(r.brand)}`, `"line": ${py(r.line)}`, `"expression": ${py(r.expression)}`]
  return `    "${r.id}": {${parts.join(', ')}},`
}
export const sourceModule = (r: Product) =>
  (r.brand ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
