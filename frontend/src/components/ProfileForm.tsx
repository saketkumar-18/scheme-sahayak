import { useState } from 'react'
import { Profile, STATES, OCCUPATIONS } from '../lib/api'

interface Props {
  onSubmit: (p: Profile) => void
  loading: boolean
  initial: Profile
}

type FieldKey = keyof Profile

export default function ProfileForm({ onSubmit, loading, initial }: Props) {
  const [p, setP] = useState<Profile>(initial)
  const [showMore, setShowMore] = useState(false)

  function set<K extends FieldKey>(key: K, value: Profile[K]) {
    setP((prev) => {
      const next: Profile = { ...prev }
      const record = next as Record<string, unknown>
      record[key] = value === ('' as unknown) ? undefined : value
      return next
    })
  }

  function boolSelect(key: FieldKey, label: string) {
    const value = p[key] as boolean | undefined
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white px-4 py-3">
        <span className="text-sm font-medium text-stone-700">{label}</span>
        <div className="flex gap-1">
          {[
            { v: true, l: 'Yes' },
            { v: false, l: 'No' },
          ].map((o) => (
            <button
              key={String(o.v)}
              type="button"
              onClick={() => set(key, o.v)}
              className={
                'rounded-lg px-3 py-1 text-xs font-bold transition ' +
                (value === o.v
                  ? 'bg-orange-600 text-white shadow'
                  : 'bg-stone-100 text-stone-600 hover:bg-stone-200')
              }
            >
              {o.l}
            </button>
          ))}
        </div>
      </div>
    )
  }

  const requiredFilled =
    p.age !== undefined && p.rural_or_urban !== undefined && p.annual_income !== undefined

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-lg font-bold text-stone-900">Tell us about yourself</h2>
        <p className="mt-1 text-sm text-stone-500">
          The more you fill, the more accurate your matches. Nothing is stored — this runs
          in your browser and is sent only for the matching request.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Age (years)</label>
            <input
              type="number"
              min={0}
              max={120}
              className="input"
              value={p.age ?? ''}
              onChange={(e) => set('age', e.target.value === '' ? undefined : Number(e.target.value))}
              placeholder="e.g. 32"
            />
          </div>
          <div>
            <label className="label">Gender</label>
            <select className="input" value={p.gender ?? ''} onChange={(e) => set('gender', e.target.value as Profile['gender'])}>
              <option value="">— select —</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="label">Annual family income (₹)</label>
            <input
              type="number"
              min={0}
              className="input"
              value={p.annual_income ?? ''}
              onChange={(e) =>
                set('annual_income', e.target.value === '' ? undefined : Number(e.target.value))
              }
              placeholder="e.g. 180000"
            />
          </div>
          <div>
            <label className="label">Social category</label>
            <select
              className="input"
              value={p.social_category ?? ''}
              onChange={(e) => set('social_category', e.target.value as Profile['social_category'])}
            >
              <option value="">— select —</option>
              <option value="SC">SC</option>
              <option value="ST">ST</option>
              <option value="OBC">OBC</option>
              <option value="General">General</option>
              <option value="EWS">EWS</option>
            </select>
          </div>
          <div>
            <label className="label">State</label>
            <select className="input" value={p.state ?? ''} onChange={(e) => set('state', e.target.value)}>
              <option value="">— select —</option>
              {STATES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Area</label>
            <select
              className="input"
              value={p.rural_or_urban ?? ''}
              onChange={(e) => set('rural_or_urban', e.target.value as Profile['rural_or_urban'])}
            >
              <option value="">— select —</option>
              <option value="rural">Rural</option>
              <option value="urban">Urban</option>
            </select>
          </div>
          <div>
            <label className="label">Occupation</label>
            <select className="input" value={p.occupation ?? ''} onChange={(e) => set('occupation', e.target.value)}>
              <option value="">— select —</option>
              {OCCUPATIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          className="mt-4 text-sm font-semibold text-orange-700 hover:underline"
          onClick={() => setShowMore(!showMore)}
        >
          {showMore ? '− Hide scheme-specific questions' : '+ Answer scheme-specific questions (better matches)'}
        </button>

        {showMore && (
          <div className="mt-4 grid gap-3">
            {boolSelect('is_landholding_farmer', 'Do you own/hold cultivable farmland?')}
            {boolSelect('owns_pucca_house', 'Do you (or family) own a pucca (permanent) house?')}
            {boolSelect('has_kutcha_or_homeless', 'Are you homeless or living in a kutcha house?')}
            {boolSelect('is_bpl', 'Is your household BPL / in SECC / Antyodaya list?')}
            {boolSelect('is_student', 'Are you a student (Class 11 or above)?')}
            {boolSelect('is_govt_employee', 'Are you a government employee?')}
            {boolSelect('pays_income_tax', 'Do you pay income tax?')}
            {boolSelect('family_member_govt_employee', 'Any family member a govt employee / pensioner?')}
            {boolSelect('is_street_vendor', 'Are you a street vendor / hawker?')}
            {boolSelect('is_artisan_or_tradeworker', 'Are you an artisan / traditional craftsperson?')}
            {boolSelect('wants_business_loan', 'Do you want a loan to start a new business?')}
            {boolSelect('girl_below_10_in_family', 'Any girl child below 10 in the family?')}
            {boolSelect('senior_70_plus_in_family', 'Any family member aged 70+?')}
            {boolSelect('bank_account', 'Do you have a bank account?')}
            {boolSelect('aadhaar_linked_bank', 'Is your bank account Aadhaar-linked?')}
          </div>
        )}

        <div className="mt-6 flex flex-col items-start gap-3 border-t border-stone-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-stone-400">
            {requiredFilled
              ? 'Ready to match ✓'
              : 'Tip: fill Age, Area, and Income for baseline results; more answers → sharper matches.'}
          </p>
          <div className="flex gap-3">
            <button type="button" className="btn-secondary" onClick={() => setP({})}>
              Reset
            </button>
            <button
              className="btn-primary"
              disabled={loading || !p.age || p.rural_or_urban === undefined || p.annual_income === undefined}
              onClick={() => onSubmit(p)}
            >
              {loading ? 'Matching…' : 'Find My Schemes →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
