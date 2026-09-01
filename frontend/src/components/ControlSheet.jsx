import { useEffect } from 'react'
import MixSliders from './MixSliders.jsx'
import StationPresets from './StationPresets.jsx'
import HostToggles from './HostToggles.jsx'
import RequestButtons from './RequestButtons.jsx'
import TopicsAndNews from './TopicsAndNews.jsx'

export default function ControlSheet({ open, onClose, config, updateConfig, applyContext, toggleHost, requestSegment, isPlaying, isGenerating }) {
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
        className="absolute inset-0 bg-black/60"
        style={{ backdropFilter: 'blur(2px)' }}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Mix, hosts & requests"
        className="sheet-up relative w-full sm:max-w-lg max-h-[88vh] overflow-y-auto bg-bg text-fg border-t-2 sm:border-2 border-line"
      >
        <div className="sticky top-0 bg-bg border-b-2 border-line px-4 py-3 flex items-center justify-between">
          <h2 className="font-display font-black text-lg">MIX, HOSTS &amp; REQUESTS</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-11 h-11 flex items-center justify-center border-2 border-line hover:bg-surface"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-8">
          <MixSliders config={config} onChange={updateConfig} />
          <StationPresets activeContext={config.context} onSelect={applyContext} />
          <HostToggles activeHosts={config.active_hosts} onToggle={toggleHost} />
          <RequestButtons onRequest={requestSegment} disabled={!isPlaying || isGenerating} />
          <TopicsAndNews config={config} onChange={updateConfig} />
        </div>
      </div>
    </div>
  )
}
