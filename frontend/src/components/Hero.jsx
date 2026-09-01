import { CONTEXTS } from '../constants/contexts'

// Placeholder grayscale "photography" per context slot, done as CSS
// gradients so the app has zero external image dependencies. Swap these
// backgroundImage values for real photography when available.
const BANNER_STYLES = {
  workout: 'radial-gradient(circle at 30% 20%, #4a4a4a, #0a0a0a 70%)',
  commute: 'linear-gradient(135deg, #2b2b2b 0%, #050505 60%)',
  chill: 'radial-gradient(circle at 70% 80%, #3a3a3a, #0a0a0a 70%)',
  custom: 'linear-gradient(160deg, #1f1f1f 0%, #050505 50%, #2a2a2a 100%)'
}

function PlayIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="5" width="4" height="14" />
      <rect x="14" y="5" width="4" height="14" />
    </svg>
  )
}

function SkipIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 5v14l10-7z" />
      <rect x="17" y="5" width="3" height="14" />
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
  onSkip
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
    <div
      className="relative w-full overflow-hidden border-b-2 border-line"
      style={{ backgroundImage: BANNER_STYLES[preset.id] || BANNER_STYLES.commute, minHeight: '70vh' }}
    >
      <div
        className="absolute inset-0"
        style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.35) 55%, rgba(0,0,0,0.15) 100%)' }}
      />

      <div className="relative flex flex-col justify-between h-full min-h-[70vh] px-4 py-6 sm:px-8 text-white">
        <div>
          <p className="font-display text-xs tracking-[0.3em] text-white/70">{preset.showName.toUpperCase()}</p>
          <p className="font-display text-sm text-white/60 mt-1">{preset.tagline}</p>
          <p className="font-display text-xs tracking-widest text-white/50 mt-3">
            ON AIR: {activeHosts || 'ALEX'}
          </p>
        </div>

        <div className="flex flex-col items-center gap-6 py-6">
          <div className="flex items-center gap-4">
            <button
              onClick={togglePlayback}
              className="w-20 h-20 rounded-full bg-accent border-2 border-white flex items-center justify-center text-white active:scale-95 transition-transform shadow-lg"
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>
            {isPlaying && (
              <button
                onClick={onSkip}
                className="w-11 h-11 rounded-full bg-white/10 border-2 border-white/60 flex items-center justify-center text-white active:scale-95 transition-transform"
                aria-label="Skip to next song"
                title="Skip song"
              >
                <SkipIcon />
              </button>
            )}
          </div>

          <div className="w-full max-w-md text-center fade-in" key={title}>
            <p className="font-display text-[11px] tracking-[0.3em] text-accent font-bold">{kicker}</p>
            <p className="font-display text-lg sm:text-xl font-bold mt-1 truncate">{title}</p>
            <p className="text-sm text-white/70 mt-1 line-clamp-2">{subtitle}</p>
            {isGenerating && <p className="text-xs text-white/50 mt-1">generating…</p>}
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <p className="font-display text-xs text-white/50 truncate">
            Up next: {upNextHint(config)}
          </p>
          <button
            onClick={onOpenSheet}
            className="shrink-0 px-4 py-3 min-h-[44px] bg-white text-black font-display text-xs font-bold tracking-widest border-2 border-white active:bg-white/90"
          >
            MIX, HOSTS &amp; REQUESTS
          </button>
        </div>
      </div>
    </div>
  )
}
