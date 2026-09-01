export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null

  return (
    <div
      className="fixed left-4 right-4 bottom-4 sm:left-auto sm:right-6 sm:bottom-6 sm:max-w-sm z-40 rounded-lg bg-error-container text-on-error-container px-4 py-3.5 flex items-center justify-between gap-3 fade-in"
      style={{ boxShadow: '0 2px 8px var(--m3-shadow), 0 6px 16px var(--m3-shadow)' }}
    >
      <p className="text-sm font-display">{message}</p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
    </div>
  )
}
