import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'

export default function RecentlyPlayed() {
  const [tracks, setTracks] = useState(null) // null = loading
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setError(null)
    api
      .getRecentTracks(10)
      .then((r) => {
        if (!cancelled) setTracks(r.recent_tracks || [])
      })
      .catch((err) => {
        if (cancelled) return
        setTracks([])
        setError(err instanceof ApiError ? err.message : "Couldn't load recent tracks")
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  return (
    <section className="border-2 border-line p-4 sm:p-5">
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-4">RECENTLY PLAYED</h3>

      {tracks === null && <p className="text-sm text-muted">Loading…</p>}

      {error && (
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="text-muted">{error}</span>
          <button
            onClick={() => setAttempt((a) => a + 1)}
            className="px-3 py-2 min-h-[44px] border-2 border-line font-display text-xs font-bold hover:bg-surface"
          >
            RETRY
          </button>
        </div>
      )}

      {tracks && tracks.length === 0 && !error && (
        <p className="text-sm text-muted">Nothing scrobbled recently.</p>
      )}

      {tracks && tracks.length > 0 && (
        <ul className="divide-y divide-line/20">
          {tracks.map((t, i) => {
            const artist = typeof t.artist === 'object' ? t.artist['#text'] : t.artist
            const image = Array.isArray(t.image) ? t.image.find((im) => im.size === 'small')?.['#text'] : null
            return (
              <li key={i} className="flex items-center gap-3 py-2.5">
                {image ? (
                  <img src={image} alt="" width="40" height="40" className="border border-line grayscale" />
                ) : (
                  <div className="w-10 h-10 border border-line bg-surface" />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate">{t.name}</p>
                  <p className="text-xs text-muted truncate">{artist}</p>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
