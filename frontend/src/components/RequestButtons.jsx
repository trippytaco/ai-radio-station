const REQUESTS = [
  { context: 'motivation', label: '🎤 Motivation' },
  { context: 'ad_lib', label: '😄 Fake Ad' },
  { context: 'transition', label: '🎵 Transition' }
]

export default function RequestButtons({ onRequest, disabled, queued }) {
  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-3">REQUEST A SEGMENT</h3>
      <div className="grid grid-cols-3 gap-2">
        {REQUESTS.map((r) => (
          <button
            key={r.context}
            onClick={() => onRequest(r.context)}
            disabled={disabled}
            className="p-3 border-2 border-line min-h-[44px] font-display text-xs font-semibold bg-bg hover:bg-surface disabled:opacity-40 disabled:pointer-events-none transition-colors"
          >
            {r.label}
          </button>
        ))}
      </div>
      {disabled && <p className="text-xs text-muted mt-2">Press play first.</p>}
      {!disabled && queued && (
        <p className="text-xs text-muted mt-2">Queued - playing after the current segment.</p>
      )}
    </section>
  )
}
