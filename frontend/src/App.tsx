import { useState } from 'react'
import { api, Profile, MatchResult, SchemeSummary } from './lib/api'
import ProfileForm from './components/ProfileForm'
import ResultsView from './components/ResultsView'
import SchemeCard from './components/SchemeCard'
import AskPanel from './components/AskPanel'

type Tab = 'form' | 'results' | 'browse' | 'ask'

export default function App() {
  const [tab, setTab] = useState<Tab>('form')
  const [profile, setProfile] = useState<Profile>({})
  const [results, setResults] = useState<MatchResult[]>([])
  const [matchedCount, setMatchedCount] = useState(0)
  const [schemes, setSchemes] = useState<SchemeSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [language, setLanguage] = useState<'en' | 'hi' | 'hinglish'>('en')

  const navTabs: { id: Tab; label: string }[] = [
    { id: 'form', label: '1 · Your Profile' },
    { id: 'results', label: `2 · Results${results.length ? ` (${matchedCount}✓)` : ''}` },
    { id: 'browse', label: 'All Schemes' },
    { id: 'ask', label: 'Ask a Question' },
  ]

  async function handleMatch(p: Profile) {
    setLoading(true)
    setError(null)
    setProfile(p)
    try {
      const res = await api.match(p, language, true)
      setResults(res.results)
      setMatchedCount(res.matched_count)
      setTab('results')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  async function loadSchemes() {
    if (schemes.length) return
    try {
      const res = await api.schemes()
      setSchemes(res.schemes)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load schemes')
    }
  }

  function switchTab(t: Tab) {
    if (t === 'browse') loadSchemes()
    setTab(t)
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-stone-200 bg-gradient-to-r from-orange-50 via-white to-green-50">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="flex items-center gap-3 text-2xl font-extrabold tracking-tight text-stone-900 sm:text-3xl">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-orange-500 text-xl font-bold text-white shadow">
                  स
                </span>
                Scheme Sahayak
              </h1>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-stone-600">
                Find out exactly which Indian government schemes you qualify for — PMAY,
                Ayushman Bharat, PM-KISAN, scholarships &amp; more — with application steps
                and official sources.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span
                className={
                  'rounded-full px-3 py-1 font-semibold ' +
                  (error ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700')
                }
              >
                {error ? 'API error' : 'Rules + RAG engine'}
              </span>
              <select
                className="rounded-full border border-stone-300 bg-white px-3 py-1.5 font-semibold text-stone-700"
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'en' | 'hi' | 'hinglish')}
                title="Explanation language"
              >
                <option value="en">English</option>
                <option value="hi">हिंदी</option>
                <option value="hinglish">Hinglish</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <nav className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-2 py-2 sm:px-6">
          {navTabs.map((t) => (
            <button
              key={t.id}
              onClick={() => switchTab(t.id)}
              className={
                'whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold transition ' +
                (tab === t.id
                  ? 'bg-stone-900 text-white shadow'
                  : 'text-stone-600 hover:bg-stone-100')
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
            <button className="ml-2 underline" onClick={() => setError(null)}>
              dismiss
            </button>
          </div>
        )}

        {tab === 'form' && <ProfileForm onSubmit={handleMatch} loading={loading} initial={profile} />}

        {tab === 'results' &&
          (results.length ? (
            <ResultsView results={results} />
          ) : (
            <div className="card p-10 text-center text-stone-500">
              <p className="text-lg font-semibold text-stone-700">No results yet</p>
              <p className="mt-1 text-sm">Fill your profile first (step 1) — takes ~2 minutes.</p>
            </div>
          ))}

        {tab === 'browse' &&
          (schemes.length ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {schemes.map((s) => (
                <SchemeCard key={s.id} scheme={s} />
              ))}
            </div>
          ) : (
            <p className="text-stone-500">Loading schemes…</p>
          ))}

        {tab === 'ask' && <AskPanel language={language} />}
      </main>

      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-6 text-xs leading-relaxed text-stone-500 sm:px-6">
          <p>
            <strong>Disclaimer:</strong> Scheme Sahayak is a citizen-help tool. Eligibility rules are
            modelled from official guidelines (PIB, ministry portals, NSP) as of Sep 2026 and may
            change — always verify on the official portal (linked on each scheme) before applying.
            Your profile stays in your browser; nothing is stored by this service.
          </p>
          <p className="mt-2">
            Built with FastAPI + rules engine + BM25 RAG + LLM explanations ·
            <a
              className="ml-1 font-semibold text-orange-600 hover:underline"
              href="https://github.com/saketkumar-18/scheme-sahayak"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}
