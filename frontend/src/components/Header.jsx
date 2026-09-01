import ThemeToggle from './ThemeToggle.jsx'

export default function Header({ isPlaying, theme, setTheme }) {
  return (
    <header className="flex items-center justify-between px-4 py-4 sm:px-6 border-b-2 border-line">
      <div className="flex items-center gap-2">
        <span className="font-display font-black text-xl tracking-tight">RADIOME</span>
        <span className="font-display text-xs text-muted tracking-widest hidden sm:inline">LIVE</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-display font-semibold tracking-widest">
          <span
            className={`w-2 h-2 ${isPlaying ? 'bg-accent on-air-dot' : 'bg-muted'}`}
            aria-hidden="true"
          />
          <span>{isPlaying ? 'ON AIR' : 'OFF AIR'}</span>
        </div>
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </div>
    </header>
  )
}
