export type ProductType = 'cigar' | 'bourbon'

export interface Product {
  id: string
  type: ProductType
  name: string
  brand: string | null
  line: string | null
  brand_family: string | null
  expression: string | null
  release_label: string | null
  aliases: string[] | null
  status: 'draft' | 'confirmed'
  source: 'seed' | 'ai' | 'manual' | 'maker'
  source_url: string | null
  source_checked_at: string | null
  image_url: string | null
  producer: string | null
  producer_id: string | null
  proof: number | null
  age_years: number | null
  age_label: string | null
  nas: boolean | null
  spirit_type: string | null
  mash_style: string | null
  mash_bill: string | null
  expression_type: string | null
  bottled_in_bond: boolean | null
  barrel_proof: boolean | null
  finish: string | null
  rarity: string | null
  msrp_usd: number | null
  release_year: number | null
  is_core_range: boolean | null
  length_in: number | null
  ring_gauge: number | null
  shape: string | null
  box_pressed: boolean | null
  wrapper_leaf: string | null
  wrapper_origin: string | null
  wrapper_shade: string | null
  strength: string | null
  body: string | null
  binder: string | null
  filler: string | null
  country: string | null
  discontinued: boolean | null
  catalog_included: boolean | null
  merged_into: string | null
  facts_verified_at: string | null
  facts_verified_by: string | null
  created_at: string
  updated_at: string
}

export const PRODUCT_COLUMNS = [
  'id', 'type', 'name', 'brand', 'line', 'brand_family', 'expression', 'release_label', 'aliases', 'status',
  'source', 'source_url', 'source_checked_at', 'image_url', 'producer', 'producer_id', 'proof', 'age_years',
  'age_label', 'nas', 'spirit_type', 'mash_style', 'mash_bill', 'expression_type', 'bottled_in_bond',
  'barrel_proof', 'finish', 'rarity', 'msrp_usd', 'release_year', 'is_core_range', 'length_in', 'ring_gauge',
  'shape', 'box_pressed', 'wrapper_leaf', 'wrapper_origin', 'wrapper_shade', 'strength', 'body', 'binder',
  'filler', 'country', 'discontinued', 'catalog_included', 'merged_into', 'facts_verified_at',
  'facts_verified_by', 'created_at', 'updated_at',
].join(',')

export interface Maker {
  id: string
  name: string
  type: string | null
}

export interface Scorecard {
  type: ProductType
  rows_live: number
  rows_confirmed: number
  pct_confirmed: number
  rows_complete: number
  pct_complete: number
  rows_confirmed_complete: number
  pct_confirmed_complete: number
  rows_fresh: number
  pct_fresh: number | null
  lines: number
  lines_confirmed: number
  rows_audited: number
}

export interface Edit {
  id: number
  product_id: string
  changed_by: string | null
  changed_at: string
  before: Record<string, unknown>
  after: Record<string, unknown>
}

export interface AuditCheck {
  id: number
  product_id: string
  quarter: string
  confirmed: boolean
  correct: boolean
  note: string | null
  checked_at: string
}

// Postgres enums (cellar schema), in their declared order.
export const ENUMS: Record<string, string[]> = {
  status: ['draft', 'confirmed'],
  source: ['seed', 'ai', 'manual', 'maker'],
  shape: ['parejo', 'torpedo', 'belicoso', 'perfecto', 'figurado', 'other'],
  strength: ['mild', 'mild_medium', 'medium', 'medium_full', 'full'],
  body: ['mild', 'mild_medium', 'medium', 'medium_full', 'full'],
  expression_type: ['standard', 'small_batch', 'single_barrel', 'store_pick', 'limited'],
  mash_style: ['traditional', 'wheated', 'high_rye', 'four_grain', 'rye', 'unknown'],
  rarity: ['shelf', 'limited', 'allocated', 'lottery', 'unicorn'],
  spirit_type: ['bourbon', 'rye', 'tennessee', 'american_single_malt', 'wheat_whiskey', 'blend', 'other'],
  wrapper_leaf: ['connecticut_shade', 'connecticut_broadleaf', 'habano', 'corojo', 'criollo', 'sumatra', 'cameroon',
    'san_andres', 'brazilian', 'candela', 'other', 'unknown'],
  wrapper_shade: ['claro', 'colorado', 'maduro', 'oscuro'],
}

export type FieldKind = 'text' | 'num' | 'int' | 'bool' | 'enum' | 'maker' | 'list' | 'url'
export interface Field {
  key: keyof Product
  label: string
  kind: FieldKind
  wide?: boolean
}

const IDENTITY: Field[] = [
  { key: 'name', label: 'Name', kind: 'text', wide: true },
  { key: 'brand', label: 'Brand', kind: 'text' },
]

export const FIELDS: Record<ProductType, { title: string; fields: Field[] }[]> = {
  cigar: [
    { title: 'Identity', fields: [...IDENTITY,
      { key: 'line', label: 'Line', kind: 'text' },
      { key: 'expression', label: 'Size name', kind: 'text' },
      { key: 'aliases', label: 'Aliases', kind: 'list', wide: true }] },
    { title: 'Size', fields: [
      { key: 'length_in', label: 'Length (in)', kind: 'num' },
      { key: 'ring_gauge', label: 'Ring', kind: 'int' },
      { key: 'shape', label: 'Shape', kind: 'enum' },
      { key: 'box_pressed', label: 'Box pressed', kind: 'bool' }] },
    { title: 'Blend', fields: [
      { key: 'wrapper_leaf', label: 'Wrapper leaf', kind: 'enum' },
      { key: 'wrapper_origin', label: 'Wrapper origin', kind: 'text' },
      { key: 'wrapper_shade', label: 'Wrapper shade', kind: 'enum' },
      { key: 'binder', label: 'Binder', kind: 'text' },
      { key: 'filler', label: 'Filler', kind: 'text' },
      { key: 'country', label: 'Country', kind: 'text' },
      { key: 'strength', label: 'Strength', kind: 'enum' },
      { key: 'body', label: 'Body', kind: 'enum' },
      { key: 'release_year', label: 'Release year', kind: 'int' }] },
  ],
  bourbon: [
    { title: 'Identity', fields: [...IDENTITY,
      { key: 'brand_family', label: 'Brand family', kind: 'text' },
      { key: 'expression', label: 'Expression', kind: 'text' },
      { key: 'release_label', label: 'Release label', kind: 'text' },
      { key: 'producer_id', label: 'Producer', kind: 'maker' },
      { key: 'aliases', label: 'Aliases', kind: 'list', wide: true }] },
    { title: 'Facts', fields: [
      { key: 'proof', label: 'Proof', kind: 'num' },
      { key: 'spirit_type', label: 'Spirit type', kind: 'enum' },
      { key: 'age_years', label: 'Age (yr)', kind: 'num' },
      { key: 'age_label', label: 'Age label', kind: 'text' },
      { key: 'nas', label: 'NAS', kind: 'bool' },
      { key: 'mash_style', label: 'Mash style', kind: 'enum' },
      { key: 'mash_bill', label: 'Mash bill', kind: 'text' },
      { key: 'expression_type', label: 'Expression type', kind: 'enum' },
      { key: 'bottled_in_bond', label: 'Bottled in bond', kind: 'bool' },
      { key: 'barrel_proof', label: 'Barrel proof', kind: 'bool' },
      { key: 'finish', label: 'Finish', kind: 'text' },
      { key: 'rarity', label: 'Rarity', kind: 'enum' },
      { key: 'msrp_usd', label: 'MSRP ($)', kind: 'num' },
      { key: 'release_year', label: 'Release year', kind: 'int' }] },
  ],
}

export const PROVENANCE: Field[] = [
  { key: 'source', label: 'Source', kind: 'enum' },
  { key: 'status', label: 'Status', kind: 'enum' },
  { key: 'source_url', label: 'Source URL', kind: 'url', wide: true },
  { key: 'image_url', label: 'Image URL', kind: 'url', wide: true },
]

// The columns cellar.protect_verified_facts() guards: changing any of them on a verified row
// is refused unless facts_verified_at changes in the same update.
export const PROTECTED: (keyof Product)[] = [
  'proof', 'age_years', 'age_label', 'expression_type', 'mash_style', 'bottled_in_bond', 'barrel_proof', 'rarity',
  'spirit_type', 'finish', 'mash_bill', 'msrp_usd', 'length_in', 'ring_gauge', 'shape', 'box_pressed',
  'release_year', 'wrapper_leaf', 'wrapper_origin', 'wrapper_shade', 'strength', 'body', 'binder', 'filler', 'country',
]
