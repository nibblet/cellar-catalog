import { memo, useEffect, useRef } from 'react'
import { isConfirmed, isLive, missing, targetOf } from './rules'
import type { Maker, Product, ProductType } from './types'

const fmt = (v: number | null | undefined) => (v == null ? '' : String(+v))
const label = (s: string | null | undefined) => (s ?? '').replace(/_/g, ' ')

interface Col { head: string; cls?: string; cell: (r: Product, makers: Map<string, Maker>) => React.ReactNode }

const COMMON_HEAD: Col[] = [
  { head: 'Name', cls: 'c-name', cell: (r) => r.name },
  { head: 'Brand', cls: 'c-brand', cell: (r) => (
    <>{r.brand}{targetOf(r) && <span className={`tier t${targetOf(r)!.tier}`}>T{targetOf(r)!.tier}</span>}</>
  ) },
]
const COMMON_TAIL: Col[] = [
  { head: 'Source', cls: 'c-src', cell: (r) => <span className={`src ${isConfirmed(r) ? 'ok' : ''}`}>{r.source}</span> },
  { head: '✓', cls: 'c-ver', cell: (r) => (r.facts_verified_at ? <span title={`verified ${r.facts_verified_at.slice(0, 10)}`}>✓</span> : '') },
  { head: 'Missing', cls: 'c-miss', cell: (r) => (
    <>
      {!isLive(r) && <span className="chip out">{r.merged_into ? 'merged' : r.discontinued ? 'discontinued' : 'hidden'}</span>}
      {missing(r).map((m) => <span key={m} className="chip">{m}</span>)}
    </>
  ) },
]

const COLS: Record<ProductType, Col[]> = {
  cigar: [
    ...COMMON_HEAD,
    { head: 'Line', cls: 'c-line', cell: (r) => r.line },
    { head: 'Size', cls: 'c-size', cell: (r) => r.expression },
    { head: 'Dims', cls: 'c-num', cell: (r) => (r.length_in || r.ring_gauge ? `${fmt(r.length_in)} × ${fmt(r.ring_gauge)}` : '') },
    { head: 'Wrapper', cls: 'c-wrap', cell: (r) => [label(r.wrapper_leaf === 'unknown' ? null : r.wrapper_leaf), r.wrapper_origin].filter(Boolean).join(' · ') },
    { head: 'Country', cls: 'c-country', cell: (r) => r.country },
    ...COMMON_TAIL,
  ],
  bourbon: [
    ...COMMON_HEAD,
    { head: 'Proof', cls: 'c-num', cell: (r) => fmt(r.proof) },
    { head: 'Age', cls: 'c-num', cell: (r) => r.age_label ?? fmt(r.age_years) },
    { head: 'Spirit', cls: 'c-spirit', cell: (r) => label(r.spirit_type) },
    { head: 'Producer', cls: 'c-prod', cell: (r, m) => (r.producer_id ? m.get(r.producer_id)?.name : r.producer) },
    ...COMMON_TAIL,
  ],
}

const Row = memo(function Row({ r, type, selected, makers, onSelect }: {
  r: Product; type: ProductType; selected: boolean; makers: Map<string, Maker>; onSelect: (id: string) => void
}) {
  const ref = useRef<HTMLTableRowElement>(null)
  useEffect(() => { if (selected) ref.current?.scrollIntoView({ block: 'nearest' }) }, [selected])
  return (
    <tr ref={ref} className={selected ? 'sel' : ''} onClick={() => onSelect(r.id)}>
      {COLS[type].map((c) => <td key={c.head} className={c.cls}>{c.cell(r, makers)}</td>)}
    </tr>
  )
})

export function Table({ rows, type, selectedId, makers, onSelect }: {
  rows: Product[]; type: ProductType; selectedId: string | null; makers: Map<string, Maker>; onSelect: (id: string) => void
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{COLS[type].map((c) => <th key={c.head} className={c.cls}>{c.head}</th>)}</tr></thead>
        <tbody>
          {rows.map((r) => <Row key={r.id} r={r} type={type} selected={r.id === selectedId} makers={makers} onSelect={onSelect} />)}
        </tbody>
      </table>
      {rows.length === 0 && <p className="empty">Nothing in this queue.</p>}
    </div>
  )
}
