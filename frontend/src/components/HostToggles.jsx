import { HOSTS } from '../constants/contexts'

export default function HostToggles({ activeHosts, onToggle }) {
  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-3">DJ ON AIR</h3>
      <div className="flex gap-2">
        {Object.values(HOSTS).map((host) => {
          const active = (activeHosts || []).includes(host.id)
          return (
            <button
              key={host.id}
              onClick={() => onToggle(host.id)}
              className={`flex-1 p-3 border-2 border-line min-h-[44px] transition-colors ${
                active ? 'bg-accent text-white' : 'bg-bg hover:bg-surface'
              }`}
              aria-pressed={active}
            >
              <div className="font-display font-bold text-sm">
                {active ? '✓ ' : ''}
                {host.name}
              </div>
              <div className={`text-xs mt-0.5 ${active ? 'text-white/80' : 'text-muted'}`}>{host.desc}</div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
