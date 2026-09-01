const OPTIONS = [
  { id: 'light', label: 'LIGHT' },
  { id: 'dark', label: 'DARK' }
]

export default function ThemeToggle({ theme, setTheme }) {
  const active = theme === 'system' ? 'light' : theme

  return (
    <div className="flex border-2 border-line" role="group" aria-label="Theme">
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          onClick={() => setTheme(opt.id)}
          className={`px-2 py-1 text-xs font-display font-bold tracking-widest transition-colors ${
            active === opt.id ? 'bg-accent text-white' : 'bg-bg text-fg hover:bg-surface'
          }`}
          aria-pressed={active === opt.id}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
