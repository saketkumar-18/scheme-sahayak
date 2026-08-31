import { SchemeSummary } from '../lib/api'

const CAT_ICON: Record<string, string> = {
  housing: '🏠',
  health: '🏥',
  agriculture: '🌾',
  education: '🎓',
  livelihood: '🛠️',
  entrepreneurship: '🚀',
  pension: '👴',
  savings: '💰',
  energy: '🔥',
}

export default function SchemeCard({ scheme }: { scheme: SchemeSummary }) {
  return (
    <div className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-2">
        <span className="text-2xl" role="img" aria-label={scheme.category}>
          {CAT_ICON[scheme.category] ?? '📋'}
        </span>
        <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-stone-500">
          {scheme.category}
        </span>
      </div>
      <h4 className="mt-3 font-bold leading-snug text-stone-900">{scheme.name}</h4>
      <p className="mt-1 text-xs text-stone-400">{scheme.ministry}</p>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">{scheme.benefit}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {scheme.sources.slice(0, 2).map((s, i) => (
          <a
            key={i}
            href={s.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-stone-200 px-2.5 py-0.5 text-[11px] font-medium text-orange-700 hover:bg-orange-50"
          >
            ↗ {s.name.split('—')[0].trim().slice(0, 28)}
          </a>
        ))}
      </div>
    </div>
  )
}
