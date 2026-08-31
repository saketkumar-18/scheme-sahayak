export interface Profile {
  age?: number
  gender?: 'male' | 'female' | 'other'
  annual_income?: number
  social_category?: 'SC' | 'ST' | 'OBC' | 'General' | 'EWS'
  state?: string
  occupation?: string
  is_landholding_farmer?: boolean
  owns_pucca_house?: boolean
  has_kutcha_or_homeless?: boolean
  is_bpl?: boolean
  is_student?: boolean
  education_level?: string
  is_govt_employee?: boolean
  pays_income_tax?: boolean
  family_member_govt_employee?: boolean
  is_married?: boolean
  girl_below_10_in_family?: boolean
  family_size?: number
  is_street_vendor?: boolean
  has_vending_certificate?: boolean
  is_artisan_or_tradeworker?: boolean
  wants_business_loan?: boolean
  senior_70_plus_in_family?: boolean
  rural_or_urban?: 'rural' | 'urban'
  disability?: boolean
  widow?: boolean
  bank_account?: boolean
  aadhaar_linked_bank?: boolean
}

export interface Criterion {
  field: string
  op?: string
  expected?: unknown
  actual?: unknown
  note?: string
}

export interface MatchResult {
  scheme_id: string
  name: string
  category: string
  benefit: string
  matched: boolean
  confidence: 'full' | 'missing_info' | 'excluded'
  score: number
  matched_criteria: Criterion[]
  missing_info: Criterion[]
  blockers: string[]
  explanation?: { text: string; backend: string; citations: { n: number; scheme_id: string; source_file: string }[] }
}

export interface SchemeSummary {
  id: string
  name: string
  ministry?: string
  category: string
  benefit: string
  summary: string
  sources: { name: string; url: string }[]
}

export interface SchemeDetail extends SchemeSummary {
  rules: unknown[]
  application_steps: string[]
  docs: string[]
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${detail.slice(0, 200)}`)
  }
  return res.json() as Promise<T>
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<{ status: string; corpus: { schemes: number; chunks: number; vector_layer: boolean } }>('/api/health'),
  schemes: () => get<{ count: number; schemes: SchemeSummary[] }>('/api/schemes'),
  scheme: (id: string) => get<SchemeDetail>(`/api/schemes/${id}`),
  match: (profile: Profile, language: 'en' | 'hi' | 'hinglish', include_explanations = true) =>
    post<{ profile: Profile; matched_count: number; results: MatchResult[] }>('/api/match', {
      profile,
      language,
      include_explanations,
      max_explanations: 3,
    }),
  explain: (profile: Profile, scheme_id: string, language: 'en' | 'hi' | 'hinglish') =>
    post<{ match: MatchResult; explanation: { text: string; backend: string; citations: unknown[] }; scheme: SchemeSummary }>('/api/explain', {
      profile,
      scheme_id,
      language,
    }),
  ask: (question: string, scheme_id?: string, language: 'en' | 'hi' | 'hinglish' = 'en') =>
    post<{ answer: { text: string; backend: string; citations: unknown[] }; question: string }>('/api/ask', {
      question,
      scheme_id,
      language,
    }),
}

export const STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa',
  'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland',
  'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
  'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Jammu & Kashmir', 'Ladakh', 'Puducherry',
]

export const OCCUPATIONS = [
  'farmer', 'daily-wage labourer', 'street vendor', 'artisan / craftsperson', 'student',
  'homemaker', 'self-employed / small business', 'private-sector employee',
  'government employee', 'retired / pensioner', 'unemployed', 'other',
]
