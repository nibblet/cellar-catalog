// Targets read from SCORECARD.md, so that file stays the one place they are set.
import scorecardMd from '../../SCORECARD.md?raw'
import { TARGETS, isConfirmed, isLive } from './rules'
import type { Product, ProductType, Scorecard } from './types'

const cells = (line: string) => line.split('|').slice(1, -1).map((c) => c.trim())
const pct = (s: string) => { const m = s.match(/(\d+(?:\.\d+)?)\s*%/); return m ? Number(m[1]) : null }

export interface QuarterTarget { quarter: string; label: string; pct: number }

/** The north-star table: `| Cigars confirmed & complete | baseline | 55% ✓ … | 65% | …` under a `| | Baseline | Q4 2026 | …` header. */
export const NORTH_STAR: Record<ProductType, QuarterTarget[]> = (() => {
  const out: Record<ProductType, QuarterTarget[]> = { cigar: [], bourbon: [] }
  const lines = scorecardMd.split('\n')
  const head = lines.find((l) => /^\|\s*\|\s*Baseline/.test(l))
  if (!head) return out
  const quarters = cells(head).map((h) => h.match(/Q([1-4])\s+(\d{4})/))
  for (const l of lines) {
    const type: ProductType | null = /^\|\s*Cigars confirmed & complete/.test(l) ? 'cigar' : /^\|\s*Bourbon confirmed & complete/.test(l) ? 'bourbon' : null
    if (!type) continue
    cells(l).forEach((c, i) => {
      const q = quarters[i]
      const p = pct(c)
      if (q && p != null) out[type].push({ quarter: `${q[2]}-Q${q[1]}`, label: `Q${q[1]} ${q[2]}`, pct: p })
    })
  }
  return out
})()

/** The supporting-metrics table: `| Provenance | … | ≥ 90% |`. Stated once, for the catalog as a whole. */
export const SUPPORTING: Record<string, number> = (() => {
  const out: Record<string, number> = {}
  for (const l of scorecardMd.split('\n')) {
    const c = cells(l)
    if (c.length < 4) continue
    const t = c[c.length - 1]
    if (c[0] === 'Brand coverage') {
      const t1 = t.match(/Tier 1[^,]*?(\d+)%/), t2 = t.match(/Tier 2[^,]*?(\d+)%/)
      if (t1) out['Brand coverage T1'] = Number(t1[1])
      if (t2) out['Brand coverage T2'] = Number(t2[1])
    } else if (/≥/.test(t) && pct(t) != null) out[c[0]] = pct(t)!
  }
  return out
})()

export interface Progress {
  value: number | null     // percent
  target: number | null    // percent
  met: boolean
  toGo: number | null      // rows (or brands / lines) still needed
}

const progress = (have: number, of: number, target: number | undefined): Progress => {
  const value = of ? Math.round((1000 * have) / of) / 10 : null
  if (target == null) return { value, target: null, met: false, toGo: null }
  const need = Math.max(0, Math.ceil((target / 100) * of - 1e-9) - have)
  return { value, target, met: need === 0, toGo: need }
}

export interface NorthStar {
  value: number
  due: QuarterTarget | null      // the nearest target not yet past
  dueMet: boolean
  next: QuarterTarget | null     // the first target from now on that isn't met yet
  toGo: number
  all: (QuarterTarget & { met: boolean })[]
}

export function northStar(sc: Scorecard, type: ProductType, quarter: string): NorthStar {
  const have = sc.rows_confirmed_complete, of = sc.rows_live
  const met = (t: QuarterTarget) => have >= Math.ceil((t.pct / 100) * of - 1e-9)
  const ahead = NORTH_STAR[type].filter((t) => t.quarter >= quarter)
  const next = ahead.find((t) => !met(t)) ?? null
  return {
    value: sc.pct_confirmed_complete,
    due: ahead[0] ?? null,
    dueMet: ahead[0] ? met(ahead[0]) : false,
    next,
    toGo: next ? Math.ceil((next.pct / 100) * of - 1e-9) - have : 0,
    all: NORTH_STAR[type].map((t) => ({ ...t, met: met(t) })),
  }
}

export function supporting(sc: Scorecard, rows: Product[], type: ProductType) {
  // Tier 1 brand coverage is a cigar measure: targets.yml's bourbon list is by producer, not brand.
  let tier1: Progress | null = null
  if (type === 'cigar') {
    const t1 = [...TARGETS.entries()].filter(([name, t]) => t.tier === 1 && rows.some((r) => r.type === 'cigar' && (r.brand ?? '').toLowerCase() === name))
    const covered = t1.filter(([name]) => rows.some((r) => r.type === 'cigar' && isLive(r) && isConfirmed(r) && (r.brand ?? '').toLowerCase() === name))
    tier1 = progress(covered.length, t1.length, SUPPORTING['Brand coverage T1'])
  }
  return {
    confirmed: progress(sc.rows_confirmed, sc.rows_live, SUPPORTING['Provenance']),
    complete: progress(sc.rows_complete, sc.rows_live, SUPPORTING['Completeness']),
    lines: progress(sc.lines_confirmed, sc.lines, SUPPORTING['Line coverage']),
    fresh: progress(sc.rows_fresh, sc.rows_confirmed, SUPPORTING['Freshness']),
    tier1,
    auditTarget: SUPPORTING['Audit accuracy'] ?? null,
  }
}
