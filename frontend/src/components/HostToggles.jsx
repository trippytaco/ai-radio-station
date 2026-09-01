import { HOSTS } from '../constants/contexts'

export default function HostToggles({ activeHosts, onToggle }) {
  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-3">DJ ON AIR</h3>
      <div className="flex gap-2.5">
        {Object.values(HOSTS).map((host) => {
          const active = (activeHosts || []).includes(host.id)
          return (
            <button
              key={host.id}
              onClick={() => onToggle(host.id)}
              className={`flex-1 flex items-center gap-2.5 p-3.5 rounded-lg min-h-[44px] transition-colors ${
                active ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-low text-on-surface border border-outline-variant'
              }`}
              aria-pressed={active}
            >
              <div
                className={`w-8 h-8 rounded-md flex items-center justify-center text-xs font-extrabold shrink-0 ${
                  active ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'
                }`}
              >
                {host.name[0]}
              </div>
              <div className="text-left">
                <div className="font-display font-bold text-sm">{host.name}</div>
                <div className={`text-xs ${active ? 'text-on-primary-container' : 'text-on-surface-variant'}`}>{host.desc}</div>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
