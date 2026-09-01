function timeAgo(iso) {
  if (!iso) return ''
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.round(mins / 60)}h ago`
}

export default function RecentTalk({ segments }) {
  if (!segments.length) return null

  return (
    <section className="rounded-xl bg-surface-container-low p-4 sm:p-5">
      <h3 className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-4">RECENT TALK</h3>
      <ul className="space-y-4 max-h-80 overflow-y-auto">
        {segments.map((seg, i) => (
          <li key={`${seg.timestamp}-${i}`} className="border-b border-outline-variant pb-3 last:border-0 last:pb-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-display font-bold tracking-widest bg-tertiary-container text-on-tertiary-container">
                {(seg.context || 'talk').replace('_', ' ').toUpperCase()}
              </span>
              <span className="text-xs font-display font-semibold text-on-surface">{seg.host}</span>
              <span className="text-xs text-on-surface-variant ml-auto">{timeAgo(seg.timestamp)}</span>
            </div>
            <p className="text-sm text-on-surface">{seg.text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
