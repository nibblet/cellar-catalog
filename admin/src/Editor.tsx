import { useEffect, useMemo, useRef, useState } from 'react'
import { loadHistory, mergeProduct, recordAudit, refetchProduct, updateProduct } from './data'
import { cigarName, isConfirmed, isLive, missing, overridesEntry, refiled, sourceModule } from './rules'
import { ENUMS, FIELDS, PROTECTED, PROVENANCE, type AuditCheck, type Edit, type Field, type Maker, type Product } from './types'

type Form = Record<string, string>

function toForm(r: Product, fields: Field[]): Form {
  const f: Form = {}
  for (const { key, kind } of fields) {
    const v = r[key]
    f[key] = v == null ? '' : kind === 'list' ? (v as string[]).join(', ') : String(v)
  }
  return f
}

function parse(kind: Field['kind'], s: string): unknown {
  const t = s.trim()
  switch (kind) {
    case 'num': { if (!t) return null; const n = Number(t); if (Number.isNaN(n)) throw new Error(`"${s}" is not a number`); return n }
    case 'int': { if (!t) return null; const n = Number(t); if (!Number.isInteger(n)) throw new Error(`"${s}" is not a whole number`); return n }
    case 'bool': return t === '' ? null : t === 'true'
    case 'list': { const a = t.split(',').map((x) => x.trim()).filter(Boolean); return a.length ? a : null }
    default: return t || null
  }
}
const same = (a: unknown, b: unknown) =>
  JSON.stringify(Array.isArray(a) && !a.length ? null : a ?? null) === JSON.stringify(Array.isArray(b) && !b.length ? null : b ?? null)

const typing = (e: KeyboardEvent) => {
  const t = e.target as HTMLElement
  return t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA'
}

export function Editor({ row, makers, userId, candidates, audit, inAudit, onChanged, onAudited, onDirtyChange }: {
  row: Product
  makers: Maker[]
  userId: string
  candidates: Product[]
  audit: AuditCheck | undefined
  inAudit: boolean
  onChanged: (rows: Product[]) => void
  onAudited: (a: AuditCheck) => void
  onDirtyChange: (dirty: boolean) => void
}) {
  const fields = useMemo(() => [...FIELDS[row.type].flatMap((g) => g.fields), ...PROVENANCE], [row.type])
  const [form, setForm] = useState<Form>(() => toForm(row, fields))
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [history, setHistory] = useState<Edit[]>([])
  const [historyTick, setHistoryTick] = useState(0)
  const [note, setNote] = useState('')
  const [merging, setMerging] = useState(false)
  const firstInput = useRef<HTMLInputElement>(null)

  useEffect(() => { setForm(toForm(row, fields)); setNote('') }, [row, fields])
  useEffect(() => {
    let live = true
    loadHistory(row.id).then((h) => live && setHistory(h)).catch(() => live && setHistory([]))
    return () => { live = false }
  }, [row.id, historyTick])

  const patch = useMemo(() => {
    const p: Record<string, unknown> = {}
    const errors: string[] = []
    for (const f of fields) {
      try {
        const v = parse(f.kind, form[f.key] ?? '')
        if (!same(v, row[f.key])) p[f.key] = v
      } catch (e) { errors.push(`${f.label}: ${(e as Error).message}`) }
    }
    return { p, errors }
  }, [form, row, fields])
  const dirty = Object.keys(patch.p).length > 0
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(true); setMsg(null)
    try { await fn(); setMsg({ kind: 'ok', text: label }); setHistoryTick((t) => t + 1) }
    catch (e) { setMsg({ kind: 'error', text: (e as Error).message }) }
    finally { setBusy(false) }
  }

  const stamp = () => ({ facts_verified_at: new Date().toISOString(), facts_verified_by: userId })

  /** Save the form. A verified row's protected facts can only change with a fresh verification stamp. */
  async function save(verify: boolean): Promise<Product | null> {
    if (patch.errors.length) throw new Error(patch.errors.join('; '))
    const p: Partial<Product> = { ...patch.p }
    const touchesProtected = Object.keys(p).some((k) => PROTECTED.includes(k as keyof Product))
    if (verify || (row.facts_verified_at && touchesProtected)) Object.assign(p, stamp())
    if (!Object.keys(p).length) return null
    const updated = await updateProduct(row.id, p)
    onChanged([updated])
    return updated
  }

  const doSave = (verify: boolean) => run(verify ? 'Saved and verified' : 'Saved', async () => {
    const r = await save(verify)
    if (!r) throw new Error('Nothing to save')
  })
  const doSet = (label: string, p: Partial<Product>) => run(label, async () => { onChanged([await updateProduct(row.id, p)]) })

  const auditCorrect = () => run('Audit: correct — verified', async () => {
    if (dirty) throw new Error('You have unsaved edits — use "Was wrong" to save the fix')
    onAudited(await recordAudit(row, true, isConfirmed(row), note || null))
    onChanged([await updateProduct(row.id, stamp())])
  })
  const auditWrong = () => run('Audit: fixed and verified', async () => {
    if (!dirty) throw new Error('Correct the wrong fields first, then record it')
    const confirmed = isConfirmed(row)
    await save(true)
    onAudited(await recordAudit(row, false, confirmed, note || `fixed: ${Object.keys(patch.p).join(', ')}`))
  })

  const openSource = () => row.source_url && window.open(row.source_url, 'cellar-source')

  // Shortcuts while not typing: v verify, c audit-correct, e edit, o open source. ⌘S / ⌘↵ anywhere.
  const keys = useRef<(e: KeyboardEvent) => void>(() => {})
  const onKey = (e: KeyboardEvent) => {
    if (busy) return
    if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); doSave(false); return }
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); doSave(true); return }
    if (e.key === 'Escape' && typing(e)) { (e.target as HTMLElement).blur(); return }
    if (typing(e) || e.metaKey || e.ctrlKey || e.altKey) return
    if (e.key === 'v') doSave(true)
    else if (e.key === 'c' && inAudit && !audit) auditCorrect()
    else if (e.key === 'e') { e.preventDefault(); firstInput.current?.focus() }
    else if (e.key === 'o') openSource()
  }
  useEffect(() => { keys.current = onKey })
  useEffect(() => {
    const h = (e: KeyboardEvent) => keys.current(e)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  const suggested = row.type === 'cigar' ? cigarName(form.line || null, form.expression || null) : ''
  const wasRefiled = row.source === 'maker' && history.some((e) => e.changed_by && refiled(e))
  const gaps = missing(row)

  const input = (f: Field, i: number) => {
    const v = form[f.key] ?? ''
    const set = (s: string) => setForm((prev) => ({ ...prev, [f.key]: s }))
    const changed = f.key in patch.p
    const common = { id: `f-${f.key}`, className: changed ? 'changed' : '' }
    let el: React.ReactNode
    if (f.kind === 'enum') {
      el = <select {...common} value={v} onChange={(e) => set(e.target.value)}>
        <option value="">—</option>
        {ENUMS[f.key]?.map((o) => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
      </select>
    } else if (f.kind === 'bool') {
      el = <select {...common} value={v} onChange={(e) => set(e.target.value)}>
        <option value="">—</option><option value="true">yes</option><option value="false">no</option>
      </select>
    } else if (f.kind === 'maker') {
      el = <select {...common} value={v} onChange={(e) => set(e.target.value)}>
        <option value="">—</option>
        {makers.filter((m) => !m.type || m.type === row.type).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
      </select>
    } else {
      el = <input {...common} ref={i === 0 ? firstInput : undefined} value={v} onChange={(e) => set(e.target.value)}
        inputMode={f.kind === 'num' || f.kind === 'int' ? 'decimal' : undefined} spellCheck={false} />
    }
    return (
      <label key={f.key} className={`field ${f.wide ? 'wide' : ''}`}>
        <span>{f.label}{changed && <em title={`was: ${JSON.stringify(row[f.key])}`}> •</em>}</span>
        {el}
      </label>
    )
  }

  let idx = 0
  return (
    <aside className="editor">
      <header className="ed-head">
        <div className="ed-title">
          {row.image_url && <img src={row.image_url} alt="" loading="lazy" />}
          <div>
            <h2>{row.name}</h2>
            <div className="badges">
              <span className={`badge ${isConfirmed(row) ? 'ok' : ''}`}>{isConfirmed(row) ? 'confirmed' : row.source}</span>
              <span className={`badge ${gaps.length ? 'warn' : 'ok'}`}>{gaps.length ? `missing ${gaps.join(', ')}` : 'complete'}</span>
              {row.facts_verified_at && <span className="badge ok">verified {row.facts_verified_at.slice(0, 10)}</span>}
              {!isLive(row) && <span className="badge out">{row.merged_into ? 'merged' : row.discontinued ? 'discontinued' : 'hidden'}</span>}
              {row.status === 'draft' && <span className="badge">draft</span>}
            </div>
          </div>
        </div>
        <div className="row">
          <button onClick={openSource} disabled={!row.source_url} title="o">Open maker page ↗</button>
          <button onClick={() => navigator.clipboard.writeText(row.id)} title="Copy row id">Copy id</button>
        </div>
      </header>

      {inAudit && (
        <section className="audit">
          <h3>Audit · {audit ? (audit.correct ? 'checked: correct' : 'checked: was wrong') : 'not yet checked'}</h3>
          {!audit && <>
            <p className="muted">Compare size, wrapper, binder, filler, body and country with the maker's page (o).</p>
            <input placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            <div className="row">
              <button className="good" disabled={busy} onClick={auditCorrect} title="c">Correct ✓</button>
              <button className="bad" disabled={busy} onClick={auditWrong}>Was wrong — save fix</button>
            </div>
          </>}
          {audit?.note && <p className="muted">{audit.note}</p>}
        </section>
      )}

      {row.facts_verified_at && (
        <p className="note">Verified rows are protected from importers. Changing a fact here re-stamps the verification.</p>
      )}

      {FIELDS[row.type].map((g) => (
        <fieldset key={g.title}>
          <legend>{g.title}</legend>
          <div className="grid">{g.fields.map((f) => input(f, idx++))}</div>
          {g.title === 'Identity' && suggested && suggested !== form.name && (
            <p className="hint">Name by convention: <b>{suggested}</b>{' '}
              <button className="link" onClick={() => setForm((p) => ({ ...p, name: suggested }))}>use</button></p>
          )}
        </fieldset>
      ))}
      <fieldset>
        <legend>Provenance</legend>
        <div className="grid">{PROVENANCE.map((f) => input(f, idx++))}</div>
      </fieldset>

      <div className="actions">
        <button className="primary" disabled={busy || !dirty} onClick={() => doSave(false)} title="⌘S">Save</button>
        <button disabled={busy} onClick={() => doSave(true)} title="⌘↵ or v">{dirty ? 'Save & verify' : 'Verify'}</button>
        {dirty && <button disabled={busy} onClick={() => setForm(toForm(row, fields))}>Revert</button>}
        <span className="spacer" />
        {row.facts_verified_at && <button disabled={busy} onClick={() => doSet('Unverified', { facts_verified_at: null, facts_verified_by: null })}>Unverify</button>}
      </div>
      {patch.errors.length > 0 && <p className="error">{patch.errors.join('; ')}</p>}
      {msg && <p className={msg.kind === 'error' ? 'error' : 'ok'}>{msg.text}</p>}

      <fieldset>
        <legend>Catalog</legend>
        <div className="row">
          <button disabled={busy} onClick={() => doSet(row.discontinued ? 'Marked current' : 'Marked discontinued', { discontinued: !row.discontinued })}>
            {row.discontinued ? 'Un-discontinue' : 'Discontinued'}</button>
          <button disabled={busy} onClick={() => doSet(row.catalog_included === false ? 'Included' : 'Hidden', { catalog_included: row.catalog_included === false })}>
            {row.catalog_included === false ? 'Include in catalog' : 'Hide from catalog'}</button>
          {!row.merged_into && <button disabled={busy} onClick={() => setMerging((m) => !m)}>Merge into…</button>}
        </div>
        {merging && <Merge row={row} candidates={candidates} busy={busy} onMerge={(target, release) => run(`Merged into ${target.name}`, async () => {
          await mergeProduct(row.id, target.id, release)
          onChanged([await refetchProduct(row.id), await refetchProduct(target.id)])
          setMerging(false)
        })} />}
      </fieldset>

      {wasRefiled && (
        <fieldset>
          <legend>OVERRIDES</legend>
          <p className="hint">Re-filed by hand. Add this to <code>catalog/sources/{sourceModule(row)}.py</code> (or the source that crawls {row.source_url && new URL(row.source_url).host}) so the next run agrees:</p>
          <pre className="snippet">{overridesEntry(row)}</pre>
          <button onClick={() => navigator.clipboard.writeText(overridesEntry(row))}>Copy</button>
        </fieldset>
      )}

      <fieldset>
        <legend>History</legend>
        {history.length === 0 && <p className="muted">No recorded changes (the log starts 2026-09-24).</p>}
        <ul className="history">
          {history.map((e) => (
            <li key={e.id}>
              <span className="muted">{new Date(e.changed_at).toLocaleString()} · {e.changed_by === userId ? 'you' : e.changed_by ? `admin ${e.changed_by.slice(0, 8)}` : 'SQL / importer'}</span>
              {Object.keys(e.after).filter((k) => k !== 'facts_verified_by').map((k) => (
                <div key={k} className="change"><b>{k}</b> <s>{fmtv(e.before[k])}</s> → {fmtv(e.after[k])}</div>
              ))}
            </li>
          ))}
        </ul>
      </fieldset>
      <p className="muted small">id {row.id} · updated {new Date(row.updated_at).toLocaleString()}</p>
    </aside>
  )
}

const fmtv = (v: unknown) => (v == null ? '∅' : typeof v === 'string' ? v : JSON.stringify(v))

function Merge({ row, candidates, busy, onMerge }: {
  row: Product; candidates: Product[]; busy: boolean; onMerge: (target: Product, release: string | null) => void
}) {
  const [q, setQ] = useState('')
  const [release, setRelease] = useState('')
  const hits = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean)
    if (!words.length) return []
    return candidates.filter((c) => c.id !== row.id && words.every((w) => `${c.brand} ${c.name}`.toLowerCase().includes(w))).slice(0, 8)
  }, [q, candidates, row.id])
  return (
    <div className="merge">
      <p className="hint">Keeps the other row. Member saves, tastings, reviews and images move to it; this row is hidden with <code>merged_into</code> set.</p>
      <input autoFocus placeholder="Search the row to keep…" value={q} onChange={(e) => setQ(e.target.value)} />
      <input placeholder="Release label for this row's tastings (optional)" value={release} onChange={(e) => setRelease(e.target.value)} />
      <ul className="hits">
        {hits.map((h) => (
          <li key={h.id}>
            <span>{h.brand} · {h.name} <span className="muted">{h.source}{h.facts_verified_at ? ' · verified' : ''}</span></span>
            <button disabled={busy} onClick={() => confirm(`Merge "${row.name}" into "${h.name}"?`) && onMerge(h, release.trim() || null)}>Merge</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
