import { CONTEXTS } from '../constants/contexts'

function PlayIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="5" width="4" height="14" rx="1.5" />
      <rect x="14" y="5" width="4" height="14" rx="1.5" />
    </svg>
  )
}

function SkipIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 5v14l10-7z" />
      <rect x="17" y="5" width="3" height="14" />
    </svg>
  )
}

function TuneIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line>
      <line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line>
      <line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line>
      <line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line>
    </svg>
  )
}

function upNextHint(config) {
  const { music_weight: m = 0, news_weight: n = 0, ad_weight: a = 0 } = config
  const total = m + n + a
  if (total <= 0) return 'more music'
  const top = [
    ['more music', m],
    ['a news break', n],
    ['a fake ad', a]
  ].sort((x, y) => y[1] - x[1])[0]
  return top[0]
}

export default function Hero({
  config,
  isPlaying,
  isGenerating,
  togglePlayback,
  currentSegment,
  nowPlayingTrack,
  onOpenSheet,
  onSkip,
  onSelectContext
}) {
  const preset = CONTEXTS[config.context] || CONTEXTS.commute
  const activeHosts = (config.active_hosts || [config.host_personality])
    .map((h) => h[0].toUpperCase() + h.slice(1))
    .join(' & ')

  const isTalking = Boolean(currentSegment)
  const kicker = isTalking ? 'TALK' : 'MUSIC'
  const title = isTalking
    ? `${currentSegment.host} — ${(currentSegment.context || 'on air').replace('_', ' ')}`
    : nowPlayingTrack
      ? nowPlayingTrack.title
      : 'Press play to start your station'
  const subtitle = isTalking
    ? currentSegment.text
    : nowPlayingTrack
      ? `${nowPlayingTrack.artist} — ${nowPlayingTrack.album}`
      : preset.tagline

  return (
    <div className="px-4 pt-3 pb-2 sm:px-6">
      {/* Hero art surface - dynamic-color gradient standing in for
          album/segment artwork until real photography is wired up. */}
      <div
        className="relative w-full rounded-xl overflow-hidden"
        style={{
          minHeight: '58vh',
          background: 'radial-gradient(120% 100% at 15% 0%, var(--m3-tertiary-container) 0%, var(--m3-primary) 46%, var(--m3-primary-container) 100%)',
          boxShadow: '0 1px 3px var(--m3-shadow), 0 8px 24px var(--m3-shadow)'
        }}
      >
        <div className="absolute top-4 left-4 flex items-center gap-1.5 pl-2.5 pr-3.5 py-1.5 rounded-full bg-surface-overlay backdrop-blur">
          <span className={`w-2 h-2 rounded-full bg-tertiary ${isPlaying ? 'on-air-dot' : ''}`} />
          <span className="font-display text-xs font-bold tracking-widest text-on-surface">{isPlaying ? 'ON AIR' : 'OFF AIR'}</span>
        </div>
        <div className="absolute top-4 right-4 px-3.5 py-1.5 rounded-full bg-surface-overlay backdrop-blur">
          <span className="font-display text-xs font-semibold text-on-surface">{activeHosts || 'Alex'}</span>
        </div>

        <div className="absolute left-5 right-5 bottom-5 text-on-primary fade-in" key={title}>
          <p className="font-display text-[11px] font-extrabold tracking-[2px] opacity-85 mb-1.5">
            {kicker} · {preset.showName.toUpperCase()}
          </p>
          <p className="font-display text-2xl font-extrabold leading-tight mb-2 truncate">{title}</p>
          <p className="text-sm leading-relaxed opacity-90 line-clamp-2 max-w-sm">{subtitle}</p>
          {isGenerating && <p className="text-xs opacity-70 mt-1">generating…</p>}
        </div>
      </div>

      {/* Wavy progress */}
      <div className="mt-4 px-1">
        <svg width="100%" height="14" viewBox="0 0 342 14" preserveAspectRatio="none" className="block">
          <path
            d="M0 7 Q4 2 8 7 T16 7 T24 7 T32 7 T40 7 T48 7 T56 7 T64 7 T72 7 T80 7 T88 7 T96 7 T104 7 T112 7 T120 7 T128 7 T136 7 T144 7 T152 7 T160 7 T168 7 T176 7 T184 7 T192 7 T200 7 T208 7 T216 7 T224 7 T232 7 T240 7 T248 7 T256 7 T264 7 T272 7 T280 7 T288 7 T296 7 T304 7 T312 7 T320 7 T328 7 T336 7 T342 7"
            fill="none" stroke="var(--m3-outline-variant)" strokeWidth="4" strokeLinecap="round"
          />
          {isPlaying && (
            <path
              d="M0 7 Q4 2 8 7 T16 7 T24 7 T32 7 T40 7 T48 7 T56 7 T64 7 T72 7 T80 7 T88 7 T96 7 T104 7 T112 7 T120 7 T128 7 T136 7"
              fill="none" stroke="var(--m3-primary)" strokeWidth="4" strokeLinecap="round"
              strokeDasharray="8" className="wave-progress"
            />
          )}
        </svg>
      </div>

      {/* Transport */}
      <div className="flex items-center justify-center gap-4 py-4">
        <button
          onClick={togglePlayback}
          className="w-[76px] h-[76px] rounded-xl bg-primary text-on-primary flex items-center justify-center active:scale-95 transition-transform"
          style={{ boxShadow: '0 4px 10px var(--m3-shadow), 0 1px 4px var(--m3-shadow)' }}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>
        {isPlaying && (
          <button
            onClick={onSkip}
            className="w-[52px] h-[52px] rounded-full bg-surface-container-high text-on-surface flex items-center justify-center active:scale-95 transition-transform"
            aria-label="Skip to next song"
            title="Skip song"
          >
            <SkipIcon />
          </button>
        )}
      </div>

      {/* Station presets */}
      <div className="mt-1">
        <p className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-2.5 px-1">WHAT ARE YOU DOING?</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {Object.values(CONTEXTS).map((p) => {
            const active = config.context === p.id
            return (
              <button
                key={p.id}
                onClick={() => onSelectContext(p.id)}
                className={`shrink-0 flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold whitespace-nowrap transition-colors ${
                  active
                    ? 'bg-primary-container text-on-primary-container'
                    : 'bg-surface-container-low text-on-surface-variant border border-outline-variant'
                }`}
              >
                <span>{p.icon}</span><span>{p.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Mix / hosts / requests entry */}
      <button
        onClick={onOpenSheet}
        className="w-full mt-5 flex items-center justify-center gap-2.5 px-5 py-4 min-h-[44px] rounded-xl bg-secondary-container text-on-secondary-container font-display text-sm font-bold active:opacity-90"
      >
        <TuneIcon />
        Mix, hosts &amp; requests
      </button>

      <p className="font-display text-xs text-on-surface-variant text-center mt-3">
        Up next: {upNextHint(config)}
      </p>
    </div>
  )
}
