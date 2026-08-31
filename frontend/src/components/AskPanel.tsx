import { useState } from 'react'
import { api } from '../lib/api'

interface Props {
  language: 'en' | 'hi' | 'hinglish'
}

const SUGGESTIONS = [
  'What is the income limit for PMAY-U 2.0?',
  'Who is excluded from PM-KISAN?',
  'How do I apply for an Ayushman card?',
  'What loans does PM Vishwakarma give?',
  'Can a General-category man get Stand-Up India?',
]

export default function AskPanel({ language }: Props) {
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [answer, setAnswer] = useState<{ text: string; backend: string; citations: unknown[] } | null>(null)
  const [err, setErr] = useState<string | null>(null)

  async function ask(question: string) {
    if (!question || question.length < 3) return
    setBusy(true)
    setErr(null)
    setAnswer(null)
    try {
      const res = await api.ask(question, undefined, language)
      setAnswer(res.answer)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="card p-6">
        <h2 className="text-lg font-bold text-stone-900">Ask about any scheme</h2>
        <p className="mt-1 text-sm text-stone-500">
          Answers are grounded in the same official guidance corpus — with citations, no
          hallucination.
        </p>
        <div className="mt-4 flex gap-2">
          <input
            className="input flex-1"
            placeholder="e.g. What is the income limit for the SC scholarship?"
            value={q}
            maxLength={500}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask(q)}
          />
          <button className="btn-primary" disabled={busy || q.length < 3} onClick={() => ask(q)}>
            {busy ? '…' : 'Ask'}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQ(s)
                ask(s)
              }}
              className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs text-stone-600 hover:border-orange-300 hover:bg-orange-50"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {err && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{err}</div>
      )}

      {answer && (
        <div className="card p-6">
          <div className="whitespace-pre-line text-sm leading-relaxed text-stone-700">
            {answer.text}
          </div>
          <p className="mt-4 text-xs text-stone-400">
            Answer engine: {answer.backend === 'pollinations' ? 'LLM (grounded)' : 'extractive'} ·
            {answer.citations.length > 0 && (
              <> cited {answer.citations.length} guidance passage{answer.citations.length > 1 ? 's' : ''}</>
            )}
          </p>
        </div>
      )}
    </div>
  )
}
