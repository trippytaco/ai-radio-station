import { CONTEXTS, CONTEXT_ORDER } from '../constants/contexts'

export default function StationPresets({ activeContext, onSelect }) {
  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-3">STATION</h3>
      <div className="grid grid-cols-2 gap-2.5">
        {CONTEXT_ORDER.map((id) => {
          const preset = CONTEXTS[id]
          const active = activeContext === id
          return (
            <button
              key={id}
              onClick={() => onSelect(id)}
              className={`text-left p-3.5 rounded-lg transition-colors min-h-[44px] ${
                active ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-low text-on-surface border border-outline-variant'
              }`}
              aria-pressed={active}
            >
              <div className="font-display font-bold text-sm">
                {preset.icon} {preset.label}
              </div>
              <div className={`text-xs mt-0.5 ${active ? 'text-on-primary-container' : 'text-on-surface-variant'}`}>{preset.desc}</div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
