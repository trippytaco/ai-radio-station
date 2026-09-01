const SLIDERS = [
  { key: 'music_weight', label: 'Music', varName: '--m3-music', textClass: 'text-music', barClass: 'bg-music' },
  { key: 'news_weight', label: 'News', varName: '--m3-news', textClass: 'text-news', barClass: 'bg-news' },
  { key: 'ad_weight', label: 'Ads', varName: '--m3-ads', textClass: 'text-ads', barClass: 'bg-ads' }
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
      <h3 className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-1">LIVE MIX</h3>
      <p className="text-xs text-on-surface-variant mb-4">Changes apply next segment — nothing playing gets cut off.</p>
      <div className="space-y-4">
        {SLIDERS.map((s) => {
          const pct = Math.round((config[s.key] || 0) * 100)
          return (
            <div key={s.key}>
              <div className="flex justify-between mb-2 font-display text-sm">
                <span className="font-semibold text-on-surface">{s.label}</span>
                <span className={`font-bold ${s.textClass}`}>{pct}%</span>
              </div>
              <div className="relative h-6 flex items-center">
                <div className="absolute left-0 right-0 h-2 rounded-full bg-surface-container-high" />
                <div className={`absolute left-0 h-2 rounded-full ${s.barClass}`} style={{ width: `${pct}%` }} />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  defaultValue={config[s.key] || 0}
                  key={`${s.key}-${config[s.key]}`}
                  onPointerUp={(e) => handleRelease(s.key, e.target.value)}
                  onKeyUp={(e) => handleRelease(s.key, e.target.value)}
                  className="relative w-full"
                  style={{ '--m3-slider-color': `var(${s.varName})` }}
                  aria-label={s.label}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
