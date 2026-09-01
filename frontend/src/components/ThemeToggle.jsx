function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <circle cx="12" cy="12" r="4"></circle>
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.35 14.5A8.5 8.5 0 0 1 9.5 3.65a8.5 8.5 0 1 0 10.85 10.85z" />
    </svg>
  )
}

const OPTIONS = [
  { id: 'light', label: 'Light', Icon: SunIcon },
  { id: 'dark', label: 'Dark', Icon: MoonIcon }
]

export default function ThemeToggle({ theme, setTheme }) {
  const active = theme === 'system' ? 'light' : theme

  return (
    <div className="flex gap-0.5 p-0.5 rounded-full bg-surface-container-high" role="group" aria-label="Theme">
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          onClick={() => setTheme(opt.id)}
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
            active === opt.id ? 'bg-primary text-on-primary' : 'text-on-surface-variant'
          }`}
          aria-pressed={active === opt.id}
          aria-label={opt.label}
          title={opt.label}
        >
          <opt.Icon />
        </button>
      ))}
    </div>
  )
}
