import { useState } from 'react'
import { MatchResult, SchemeDetail, api } from '../lib/api'

interface Props {
  results: MatchResult[]
}

const CONF_LABEL: Record<string, string> = {
  full: '✅ Eligible',
  missing_info: '🟡 Maybe — info missing',
  excluded: '❌ Not eligible',
}

export default function ResultsView({ results }: Props) {
  const [open, setOpen] = useState<string | null>(results[0]?.scheme_id ?? null)
  const [details, setDetails] = useState<Record<string, SchemeDetail>>({})
  const [busy, setBusy] = useState<string | null>(null)

  const eligible = results.filter((r) => r.matched)
  const maybe = results.filter((r) => !r.matched && r.confidence === 'missing_info')
  const excluded = results.filter((r) => r.confidence === 'excluded')

  async function toggle(id: string) {
    if (open === id) {
      setOpen(null)
      return
    }
    setOpen(id)
    if (!details[id]) {
      setBusy(id)
      try {
        const d = await api.scheme(id)
        setDetails((prev) => ({ ...prev, [id]: d }))
      } finally {
        setBusy(null)
      }
    }
  }

  function Section({ title, items, tone }: { title: string; items: MatchResult[]; tone: string }) {
    if (!items.length) return null
    return (
      <section className="mt-8 first:mt-0">
        <h3 className={'mb-3 text-sm font-bold uppercase tracking-wider ' + tone}>{title}</h3>
        <div className="space-y-3">
          {items.map((r) => {
            const isOpen = open === r.scheme_id
            const d = details[r.scheme_id]
            return (
              <div key={r.scheme_id} className="card overflow-hidden">
                <button
                  onClick={() => toggle(r.scheme_id)}
                  className="flex w-full items-center justify-between gap-4 p-4 text-left hover:bg-stone-50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-bold text-stone-900">{r.name}</p>
                    <p className="mt-0.5 text-sm text-stone-600">{r.benefit}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-stone-100 px-3 py-1 text-xs font-bold text-stone-600">
                    {CONF_LABEL[r.confidence]}
                  </span>
                </button>

                {isOpen && (
                  <div className="border-t border-stone-100 bg-stone-50/60 p-4">
                    {r.explanation && (
                      <div className="mb-4 rounded-xl border border-orange-200 bg-orange-50 p-4">
                        <p className="text-xs font-bold uppercase tracking-wide text-orange-700">
                          Why you match{' '}
                          <span className="font-normal normal-case">
                            (via {r.explanation.backend})
                          </span>
                        </p>
                        <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-stone-700">
                          {r.explanation.text}
                        </p>
                      </div>
                    )}

                    {!r.matched && r.blockers.length > 0 && (
                      <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                        <p className="font-bold">To confirm eligibility:</p>
                        <ul className="mt-1 list-disc space-y-0.5 pl-5">
                          {r.blockers.slice(0, 4).map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {busy === r.scheme_id && <p className="text-sm text-stone-400">Loading steps…</p>}
                    {d && (
                      <>
                        <p className="text-xs font-bold uppercase tracking-wide text-stone-500">
                          How to apply
                        </p>
                        <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-stone-700">
                          {d.application_steps.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ol>
                        <p className="mt-4 text-xs font-bold uppercase tracking-wide text-stone-500">
                          Documents needed
                        </p>
                        <div className="mt-1.5 flex flex-wrap gap-1.5">
                          {d.docs.map((doc, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-stone-200 px-2.5 py-0.5 text-xs font-medium text-stone-700"
                            >
                              {doc}
                            </span>
                          ))}
                        </div>
                        <p className="mt-4 text-xs font-bold uppercase tracking-wide text-stone-500">
                          Official sources
                        </p>
                        <ul className="mt-1.5 space-y-1 text-sm">
                          {d.sources.map((s, i) => (
                            <li key={i}>
                              <a
                                href={s.url}
                                target="_blank"
                                rel="noreferrer"
                                className="font-medium text-orange-700 hover:underline"
                              >
                                ↗ {s.name}
                              </a>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>
    )
  }

  return (
    <div>
      <div className="card mb-6 flex flex-wrap items-center justify-between gap-3 bg-gradient-to-r from-orange-50 to-green-50 p-5">
        <div>
          <p className="text-sm font-bold text-stone-800">
            {eligible.length} scheme{eligible.length === 1 ? '' : 's'} you likely qualify for
            {maybe.length > 0 && `, ${maybe.length} more need info`}
          </p>
          <p className="mt-0.5 text-xs text-stone-500">
            Results from a deterministic rules engine over official guidelines + RAG citations.
          </p>
        </div>
      </div>

      <Section title="✅ You likely qualify" items={eligible} tone="text-green-700" />
      <Section title="🟡 Likely eligible — provide missing info" items={maybe} tone="text-amber-600" />
      <Section title="❌ Not eligible (for your profile)" items={excluded} tone="text-stone-400" />
    </div>
  )
}
