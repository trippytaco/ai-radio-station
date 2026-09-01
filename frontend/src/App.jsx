import { useState } from 'react'
import Header from './components/Header.jsx'
import Hero from './components/Hero.jsx'
import ControlSheet from './components/ControlSheet.jsx'
import RecentTalk from './components/RecentTalk.jsx'
import RecentlyPlayed from './components/RecentlyPlayed.jsx'
import ErrorBanner from './components/ErrorBanner.jsx'
import { useRadioEngine } from './hooks/useRadioEngine.js'

export default function App() {
  const [sheetOpen, setSheetOpen] = useState(false)
  const engine = useRadioEngine()

  return (
    <div className="min-h-screen bg-bg text-fg font-body flex flex-col">
      <Header isPlaying={engine.isPlaying} theme={engine.theme} setTheme={engine.setTheme} />

      <main className="flex-1 w-full max-w-[900px] mx-auto">
        <Hero
          config={engine.config}
          isPlaying={engine.isPlaying}
          isGenerating={engine.isGenerating}
          togglePlayback={engine.togglePlayback}
          currentSegment={engine.currentSegment}
          nowPlayingTrack={engine.nowPlayingTrack}
          onOpenSheet={() => setSheetOpen(true)}
        />

        <div className="p-4 sm:p-6 grid gap-4 sm:grid-cols-2">
          <RecentTalk segments={engine.recentTalk} />
          <RecentlyPlayed />
        </div>
      </main>

      <ControlSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        config={engine.config}
        updateConfig={engine.updateConfig}
        applyContext={engine.applyContext}
        toggleHost={engine.toggleHost}
        requestSegment={engine.requestSegment}
        isPlaying={engine.isPlaying}
        isGenerating={engine.isGenerating}
      />

      <ErrorBanner message={engine.error} onDismiss={engine.dismissError} />

      {/* Hidden audio elements driving actual playback - kept in the DOM
          (not unmounted) so they survive re-renders and keep playing in
          the background regardless of what's shown on screen. */}
      <audio ref={engine.musicAudioRef} preload="none" />
      <audio ref={engine.segmentAudioRef} preload="none" />
    </div>
  )
}
