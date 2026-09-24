import type { Session } from '@supabase/supabase-js'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { loadAudits, loadMakers, loadProducts, loadRecentEdits, loadScorecard, supabase } from './data'
import { Editor } from './Editor'
import { Login } from './Login'
import { QUEUES, isLive, quarterOf, type Ctx } from './rules'
import { Table } from './Table'
import { northStar, supporting, type Progress } from './targets'
import type { AuditCheck, Edit, Maker, Product, ProductType, Scorecard } from './types'

const pref = (k: string, d: string) => { try { return localStorage.getItem(`admin.${k}`) ?? d } catch { return d } }
const setPref = (k: string, v: string) => { try { localStorage.setItem(`admin.${k}`, v) } catch { /* ignore */ } }

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [])
  if (session === undefined) return <div className="loading">Loading…</div>
  if (!session) return <Login />
  return <Admin session={session} />
}

function Admin({ session }: { session: Session }) {
  const userId = session.user.id
  const [role, setRole] = useState<string | null | undefined>(undefined)
  const [products, setProducts] = useState<Product[] | null>(null)
  const [makers, setMakers] = useState<Maker[]>([])
  const [score, setScore] = useState<Scorecard[]>([])
  const [edits, setEdits] = useState<Edit[]>([])
  const [audits, setAudits] = useState<AuditCheck[]>([])
  const [error, setError] = useState<string | null>(null)

  const [type, setType] = useState<ProductType>(() => pref('type', 'cigar') as ProductType)
  const [queueId, setQueueId] = useState(() => pref('queue', 'confirmed-incomplete'))
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [tick, setTick] = useState(0)   // bumping it re-evaluates the frozen queue
  const dirty = useRef(false)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    supabase.from('users').select('role').eq('id', userId).maybeSingle()
      .then(({ data }) => setRole((data as { role: string } | null)?.role ?? null))
  }, [userId])

  const reload = useCallback(async () => {
    setError(null)
    try {
      const [p, m, s, e, a] = await Promise.all([loadProducts(), loadMakers(), loadScorecard(), loadRecentEdits(), loadAudits()])
      setProducts(p); setMakers(m); setScore(s); setEdits(e); setAudits(a); setTick((t) => t + 1)
    } catch (e) { setError((e as Error).message) }
  }, [])
  useEffect(() => { if (role === 'admin') reload() }, [role, reload])

  // The scorecard and edit log are cheap; refresh them shortly after any write.
  const refreshTimer = useRef<number | undefined>(undefined)
  const refreshSoon = useCallback(() => {
    clearTimeout(refreshTimer.current)
    refreshTimer.current = window.setTimeout(async () => {
      try { const [s, e] = await Promise.all([loadScorecard(), loadRecentEdits()]); setScore(s); setEdits(e) } catch { /* next write retries */ }
    }, 800)
  }, [])

  const onChanged = useCallback((rows: Product[]) => {
    setProducts((prev) => {
      if (!prev) return prev
      const byId = new Map(rows.map((r) => [r.id, r]))
      return prev.map((p) => byId.get(p.id) ?? p)
    })
    refreshSoon()
  }, [refreshSoon])
  const onAudited = useCallback((a: AuditCheck) => setAudits((prev) => [...prev, a]), [])
  const onDirtyChange = useCallback((d: boolean) => { dirty.current = d }, [])

  const ctx: Ctx = useMemo(() => ({ audits, edits }), [audits, edits])
  const queueRows = useMemo(() => {
    const out = new Map<string, Product[]>()
    if (products) for (const q of QUEUES) out.set(q.id, q.rows(products, type, ctx))
    return out
  }, [products, type, ctx])

  // Rows shown: the queue, frozen while you work it so a fixed row doesn't jump out from under you.
  // Picking a queue, type or search re-evaluates it.
  const [frozen, setFrozen] = useState<string[] | null>(null)
  const freezeKey = `${type}|${queueId}|${search}|${tick}`
  const lastKey = useRef('')
  const queue = QUEUES.find((q) => q.id === queueId) ?? QUEUES[0]
  useEffect(() => {
    if (!products || lastKey.current === freezeKey) return
    lastKey.current = freezeKey
    const words = search.toLowerCase().split(/\s+/).filter(Boolean)
    let rows = queueRows.get(queue.id) ?? []
    if (words.length) {
      rows = rows.filter((r) => {
        const hay = `${r.brand} ${r.line ?? ''} ${r.name} ${r.expression ?? ''} ${(r.aliases ?? []).join(' ')} ${r.id}`.toLowerCase()
        return words.every((w) => hay.includes(w))
      })
    }
    setFrozen(rows.map((r) => r.id))
  }, [freezeKey, products, queueRows, queue.id, search])
  const byId = useMemo(() => new Map((products ?? []).map((p) => [p.id, p])), [products])
  const rows = useMemo(() => (frozen ?? []).map((id) => byId.get(id)!).filter(Boolean), [frozen, byId])
  const refreshQueue = () => setTick((t) => t + 1)

  const selected = selectedId ? byId.get(selectedId) ?? null : null
  const select = useCallback((id: string | null) => {
    if (dirty.current && !confirm('Discard unsaved changes?')) return
    dirty.current = false
    setSelectedId(id)
  }, [])

  // Keep a selection inside the list when it changes.
  useEffect(() => {
    if (rows.length && (!selectedId || !frozen?.includes(selectedId))) setSelectedId(rows[0].id)
  }, [rows, selectedId, frozen])

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      if (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return
      const i = rows.findIndex((r) => r.id === selectedId)
      if (e.key === 'j' || e.key === 'ArrowDown') { e.preventDefault(); if (i < rows.length - 1) select(rows[i + 1].id) }
      else if (e.key === 'k' || e.key === 'ArrowUp') { e.preventDefault(); if (i > 0) select(rows[i - 1].id) }
      else if (e.key === '/') { e.preventDefault(); searchRef.current?.focus() }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [rows, selectedId, select])

  const makerMap = useMemo(() => new Map(makers.map((m) => [m.id, m])), [makers])
  const candidates = useMemo(() => (products ?? []).filter((p) => p.type === type && isLive(p)), [products, type])
  const auditById = useMemo(() => new Map(audits.map((a) => [a.product_id, a])), [audits])

  if (role === undefined) return <div className="loading">Checking access…</div>
  if (role !== 'admin') return (
    <div className="login"><div className="login-card">
      <h1>Not an admin</h1>
      <p>{session.user.email} is signed in but has no admin role in <code>cellar.users</code>.</p>
      <button onClick={() => supabase.auth.signOut()}>Sign out</button>
    </div></div>
  )

  const sc = score.find((s) => s.type === type)
  const typeAudits = audits.filter((a) => byId.get(a.product_id)?.type === type)
  const auditWrongConfirmed = typeAudits.filter((a) => !a.correct && a.confirmed).length
  const sup = sc && products ? supporting(sc, products, type) : null
  const auditPct = typeAudits.length ? Math.round((100 * typeAudits.filter((a) => a.correct).length) / typeAudits.length) : null

  return (
    <div className="app">
      <header className="top">
        <div className="brand">Catalog admin</div>
        <div className="seg">
          {(['cigar', 'bourbon'] as ProductType[]).map((t) => (
            <button key={t} className={t === type ? 'on' : ''} onClick={() => { if (!dirty.current || confirm('Discard unsaved changes?')) { dirty.current = false; setType(t); setPref('type', t) } }}>
              {t === 'cigar' ? 'Cigars' : 'Bourbon'}</button>
          ))}
        </div>
        {sc && sup && (
          <div className="stats">
            <NorthStarStat sc={sc} type={type} />
            <Stat label="Confirmed" p={sup!.confirmed} />
            <Stat label="Complete" p={sup!.complete} />
            <Stat label="Lines confirmed" p={sup!.lines} unit="lines" />
            {sup!.tier1 && <Stat label="Tier 1 brands" p={sup!.tier1} unit="brands" />}
            <Stat label="Fresh" p={sup!.fresh} />
            <Stat label={`Audit ${quarterOf()}`} p={{ value: auditPct, target: sup!.auditTarget, met: auditPct != null && sup!.auditTarget != null && auditPct >= sup!.auditTarget && !auditWrongConfirmed, toGo: null }}
              extra={`${typeAudits.length} checked${auditWrongConfirmed ? ` · ${auditWrongConfirmed} confirmed wrong` : ''}`} />
          </div>
        )}
        <div className="who">
          <span className="muted">{session.user.email}</span>
          <button onClick={() => reload()} title="Reload everything">Reload</button>
          <button onClick={() => supabase.auth.signOut()}>Sign out</button>
        </div>
      </header>

      <nav className="side">
        {QUEUES.map((q) => {
          const n = queueRows.get(q.id)?.length ?? 0
          if (!n && q.id !== queueId && ['placeholders', 'wrapper-other', 'refiled', 'drafts'].includes(q.id)) return null
          return (
            <button key={q.id} className={q.id === queueId ? 'on' : ''} title={q.hint}
              onClick={() => {
                if (q.id === queueId) return refreshQueue()
                if (dirty.current && !confirm('Discard unsaved changes?')) return
                dirty.current = false; setQueueId(q.id); setPref('queue', q.id)
              }}>
              <span>{q.label}</span><span className="n">{products ? n.toLocaleString() : ''}</span>
            </button>
          )
        })}
        <div className="keys">
          <b>Keys</b>
          <div><kbd>j</kbd>/<kbd>k</kbd> next / previous</div>
          <div><kbd>/</kbd> search · <kbd>e</kbd> edit</div>
          <div><kbd>o</kbd> open maker page</div>
          <div><kbd>v</kbd> verify · <kbd>c</kbd> audit correct</div>
          <div><kbd>⌘S</kbd> save · <kbd>⌘↵</kbd> save & verify</div>
          <div><kbd>esc</kbd> leave a field</div>
        </div>
      </nav>

      <main className="list">
        <div className="list-head">
          <div>
            <h1>{queue.label} <span className="muted">{rows.length.toLocaleString()}</span></h1>
            <p className="muted">{queue.hint}</p>
          </div>
          <input ref={searchRef} className="search" placeholder="Search brand, line, name, alias, id  ( / )" value={search}
            onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') { setSearch(''); (e.target as HTMLElement).blur() } }} />
        </div>
        {error && <p className="error">{error} <button onClick={reload}>Retry</button></p>}
        {!products && !error ? <p className="loading">Loading catalog…</p> :
          <Table rows={rows} type={type} selectedId={selectedId} makers={makerMap} onSelect={select} />}
      </main>

      {selected ? (
        <Editor key={selected.id} row={selected} makers={makers} userId={userId} candidates={candidates}
          audit={auditById.get(selected.id)} inAudit={queueId === 'audit' || auditById.has(selected.id)}
          onChanged={onChanged} onAudited={onAudited} onDirtyChange={onDirtyChange} />
      ) : <aside className="editor empty">Select a row.</aside>}
    </div>
  )
}

function Stat({ label, p, unit = 'rows', extra }: { label: string; p: Progress; unit?: string; extra?: string }) {
  const state = p.target == null || p.value == null ? '' : p.met ? 'met' : 'short'
  return (
    <div className={`stat ${state}`}
      title={p.target == null ? undefined : p.met ? `Target ≥ ${p.target}% met` : `Target ≥ ${p.target}%: ${p.toGo ?? '?'} ${unit} to go`}>
      <div className="v">{p.value == null ? '—' : `${p.value}%`}</div>
      <div className="l">{label}{p.target != null && <span className="t"> · ≥ {p.target}%{p.met ? ' ✓' : p.toGo ? ` · ${p.toGo.toLocaleString()} to go` : ''}</span>}</div>
      {extra && <div className="l">{extra}</div>}
    </div>
  )
}

function NorthStarStat({ sc, type }: { sc: Scorecard; type: ProductType }) {
  const ns = northStar(sc, type, quarterOf())
  const title = ns.all.map((t) => `${t.label}: ${t.pct}%${t.met ? ' ✓' : ''}`).join('\n')
  return (
    <div className="stat big" title={`SCORECARD.md targets\n${title}`}>
      <div className="v">{ns.value}%</div>
      <div className="l">Confirmed & complete · {sc.rows_confirmed_complete.toLocaleString()} / {sc.rows_live.toLocaleString()}</div>
      <div className="l">
        {ns.due && ns.due !== ns.next && <span className="met">{ns.due.label} {ns.due.pct}% ✓ · </span>}
        {ns.next
          ? <span className="short">{ns.next.label} target {ns.next.pct}% · <b>{ns.toGo.toLocaleString()} rows to go</b></span>
          : <span className="met">every target met ✓</span>}
      </div>
    </div>
  )
}
