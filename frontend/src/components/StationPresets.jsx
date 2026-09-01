import { CONTEXTS, CONTEXT_ORDER } from '../constants/contexts'

export default function StationPresets({ activeContext, onSelect }) {
  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-3">STATION</h3>
      <div className="grid grid-cols-2 gap-2">
        {CONTEXT_ORDER.map((id) => {
          const preset = CONTEXTS[id]
          const active = activeContext === id
          return (
            <button
              key={id}
              onClick={() => onSelect(id)}
              className={`text-left p-3 border-2 border-line transition-colors min-h-[44px] ${
                active ? 'bg-accent text-white' : 'bg-bg hover:bg-surface'
              }`}
              aria-pressed={active}
            >
              <div className="font-display font-bold text-sm">
                {preset.icon} {preset.label}
              </div>
              <div className={`text-xs mt-0.5 ${active ? 'text-white/80' : 'text-muted'}`}>{preset.desc}</div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
