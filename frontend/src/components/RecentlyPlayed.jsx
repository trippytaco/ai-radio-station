function timeAgo(iso) {
  if (!iso) return ''
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.round(mins / 60)}h ago`
}

export default function RecentlyPlayed({ history }) {
  return (
    <section className="border-2 border-line p-4 sm:p-5">
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-4">RECENTLY PLAYED</h3>

      {history.length === 0 && (
        <p className="text-sm text-muted">Nothing played yet - press play to start your station.</p>
      )}

      {history.length > 0 && (
        <ul className="divide-y divide-line/20">
          {history.map((t, i) => (
            <li key={`${t.rating_key || t.key}-${i}`} className="flex items-center gap-3 py-2.5">
              <div className="w-10 h-10 border border-line bg-surface shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold truncate">{t.title}</p>
                <p className="text-xs text-muted truncate">{t.artist} — {t.album}</p>
              </div>
              <span className="text-xs text-muted shrink-0">{timeAgo(t.played_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
