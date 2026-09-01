const SLIDERS = [
  { key: 'music_weight', label: 'Music', colorClass: 'accent-music', barClass: 'bg-music' },
  { key: 'news_weight', label: 'News', colorClass: 'accent-news', barClass: 'bg-news' },
  { key: 'ad_weight', label: 'Ads', colorClass: 'accent-ads', barClass: 'bg-ads' }
]

export default function MixSliders({ config, onChange }) {
  const handleRelease = (key, rawValue) => {
    const value = parseFloat(rawValue)
    const others = SLIDERS.filter((s) => s.key !== key)
    const othersTotal = others.reduce((sum, s) => sum + (config[s.key] || 0), 0)
    const remaining = 1 - value

    const patch = { [key]: value }
    if (othersTotal > 0) {
      // Rescale the other two proportionally so everything still sums to 1.
      others.forEach((s) => {
        patch[s.key] = Math.max(0, ((config[s.key] || 0) / othersTotal) * remaining)
      })
    }
    onChange(patch)
  }

  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-3">LIVE MIX</h3>
      <p className="text-xs text-muted mb-4">Changes apply to the next segment, current one keeps playing.</p>
      <div className="space-y-5">
        {SLIDERS.map((s) => (
          <div key={s.key}>
            <div className="flex justify-between mb-1.5 font-display text-sm">
              <span className="font-semibold">{s.label}</span>
              <span className="text-muted">{Math.round((config[s.key] || 0) * 100)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              defaultValue={config[s.key] || 0}
              key={`${s.key}-${config[s.key]}`}
              onPointerUp={(e) => handleRelease(s.key, e.target.value)}
              onKeyUp={(e) => handleRelease(s.key, e.target.value)}
              className="w-full"
              aria-label={s.label}
            />
          </div>
        ))}
      </div>
    </section>
  )
}
