export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-accent text-white px-4 py-3 flex items-center justify-between gap-3 border-t-2 border-line fade-in">
      <p className="text-sm font-display">{message}</p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="shrink-0 w-9 h-9 flex items-center justify-center border-2 border-white/60 hover:bg-white/10"
      >
        ✕
      </button>
    </div>
  )
}
