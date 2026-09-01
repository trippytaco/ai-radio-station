import { useEffect } from 'react'
import MixSliders from './MixSliders.jsx'
import StationPresets from './StationPresets.jsx'
import HostToggles from './HostToggles.jsx'
import RequestButtons from './RequestButtons.jsx'
import TopicsAndNews from './TopicsAndNews.jsx'

export default function ControlSheet({ open, onClose, config, updateConfig, applyContext, toggleHost, requestSegment, isPlaying, isSegmentQueued }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
      <div
        className="absolute inset-0 bg-scrim-overlay"
        style={{ backdropFilter: 'blur(2px)' }}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Mix, hosts & requests"
        className="sheet-up relative w-full sm:max-w-lg sm:mb-6 max-h-[88vh] overflow-y-auto bg-surface text-on-surface rounded-t-xl sm:rounded-xl"
        style={{ boxShadow: '0 -2px 12px var(--m3-shadow)' }}
      >
        <div className="flex justify-center pt-3 pb-1 sm:hidden">
          <div className="w-8 h-1 rounded-full bg-outline-variant" />
        </div>

        <div className="sticky top-0 bg-surface px-5 py-3 flex items-center justify-between">
          <h2 className="font-display font-bold text-xl">Mix, hosts &amp; requests</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-9 h-9 rounded-full flex items-center justify-center bg-surface-container-high text-on-surface"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <div className="px-5 pb-8 space-y-7">
          <MixSliders config={config} onChange={updateConfig} />
          <StationPresets activeContext={config.context} onSelect={applyContext} />
          <HostToggles activeHosts={config.active_hosts} onToggle={toggleHost} />
          <RequestButtons onRequest={requestSegment} disabled={!isPlaying} queued={isSegmentQueued} />
          <TopicsAndNews config={config} onChange={updateConfig} />
        </div>
      </div>
    </div>
  )
}
