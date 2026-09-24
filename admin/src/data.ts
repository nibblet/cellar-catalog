import { createClient } from '@supabase/supabase-js'
import { quarterOf } from './rules'
import { PRODUCT_COLUMNS, type AuditCheck, type Edit, type Maker, type Product, type Scorecard } from './types'

export const supabase = createClient(import.meta.env.VITE_SUPABASE_URL, import.meta.env.VITE_SUPABASE_KEY, {
  db: { schema: 'cellar' },
})

function check<T>(res: { data: T | null; error: { message: string } | null }): T {
  if (res.error) throw new Error(res.error.message)
  return res.data as T
}

/** Every product row (admins see hidden ones too), paged past PostgREST's 1,000-row cap. */
export async function loadProducts(): Promise<Product[]> {
  const page = 1000
  const out: Product[] = []
  for (let from = 0; ; from += page) {
    const rows = check(await supabase.from('products').select(PRODUCT_COLUMNS).order('id').range(from, from + page - 1)) as unknown as Product[]
    out.push(...rows)
    if (rows.length < page) return out
  }
}

export const loadMakers = async () =>
  check(await supabase.from('makers').select('id,name,type').order('name')) as Maker[]

export const loadScorecard = async () =>
  check(await supabase.from('catalog_scorecard').select('*')) as Scorecard[]

export const loadRecentEdits = async (days = 14) =>
  check(await supabase.from('product_edits').select('*')
    .gte('changed_at', new Date(Date.now() - days * 86_400_000).toISOString())
    .order('changed_at', { ascending: false }).limit(2000)) as Edit[]

export const loadHistory = async (productId: string) =>
  check(await supabase.from('product_edits').select('*').eq('product_id', productId)
    .order('changed_at', { ascending: false }).limit(50)) as Edit[]

export const loadAudits = async () =>
  check(await supabase.from('audit_checks').select('*').eq('quarter', quarterOf())) as AuditCheck[]

export async function updateProduct(id: string, patch: Partial<Product>): Promise<Product> {
  return check(await supabase.from('products').update(patch).eq('id', id).select(PRODUCT_COLUMNS).single()) as unknown as Product
}

export async function refetchProduct(id: string): Promise<Product> {
  return check(await supabase.from('products').select(PRODUCT_COLUMNS).eq('id', id).single()) as unknown as Product
}

export async function mergeProduct(child: string, parent: string, release: string | null) {
  check(await supabase.rpc('admin_merge_product', { child, parent, release }))
}

export async function recordAudit(r: Product, correct: boolean, confirmed: boolean, note: string | null) {
  return check(await supabase.from('audit_checks')
    .insert({ product_id: r.id, quarter: quarterOf(), confirmed, correct, note }).select('*').single()) as AuditCheck
}
