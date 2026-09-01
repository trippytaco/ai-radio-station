import ThemeToggle from './ThemeToggle.jsx'

export default function Header({ isPlaying, theme, setTheme }) {
  return (
    <header className="flex items-center justify-between px-4 py-4 sm:px-6">
      <div className="flex items-center gap-2.5">
        <div className="w-9 h-9 rounded-sm bg-primary-container flex items-center justify-center shrink-0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--m3-on-primary-container)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="14" r="7"></circle>
            <circle cx="12" cy="14" r="2"></circle>
            <path d="M8 8 L12 3 L16 8"></path>
          </svg>
        </div>
        <span className="font-display font-bold text-xl tracking-tight">RadioMe</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs font-display font-semibold text-on-surface-variant">
          <span
            className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-tertiary on-air-dot' : 'bg-outline-variant'}`}
            aria-hidden="true"
          />
          <span className="hidden sm:inline">{isPlaying ? 'ON AIR' : 'OFF AIR'}</span>
        </div>
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </div>
    </header>
  )
}
