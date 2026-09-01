import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import { CONTEXTS } from '../constants/contexts'
import { useLocalStorage } from './useLocalStorage'

const TICK_MS = 12000
const SEGMENT_MAX_DISPLAY_MS = 9000
const DUCK_VOLUME_SCALE = 0.15

const DEFAULT_CONFIG = {
  music_weight: 0.5,
  news_weight: 0.3,
  ad_weight: 0.1,
  host_personality: 'alex',
  active_hosts: ['alex'],
  news_sources: ['bbc', 'guardian', 'cnn'],
  context: 'commute',
  topics: [],
  safe_mode: false
}

function weightedPick(weights) {
  // weights: { key: number }. Returns a key, or null if all weights are 0.
  const entries = Object.entries(weights).filter(([, w]) => w > 0)
  const total = entries.reduce((sum, [, w]) => sum + w, 0)
  if (total <= 0) return null
  let roll = Math.random() * total
  for (const [key, w] of entries) {
    if (roll < w) return key
    roll -= w
  }
  return entries[entries.length - 1][0]
}

export function useRadioEngine() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentSegment, setCurrentSegment] = useState(null) // AI-generated talk overlay
  const [nowPlayingTrack, setNowPlayingTrack] = useState(null) // music
  const [recentTalk, setRecentTalk] = useState([])
  const [error, setError] = useState(null)
  const [volume, setVolumeState] = useLocalStorage('radiome:volume', 0.8)
  const [theme, setTheme] = useLocalStorage('radiome:theme', 'system')

  const musicAudioRef = useRef(null)
  const segmentAudioRef = useRef(null)
  const musicQueueRef = useRef([])
  const musicIndexRef = useRef(0)
  const tickTimerRef = useRef(null)
  const segmentTimeoutRef = useRef(null)
  const configRef = useRef(config)
  configRef.current = config

  useEffect(() => {
    if (musicAudioRef.current) musicAudioRef.current.volume = volume
  }, [volume, isPlaying])

  const reportError = useCallback((err, fallback) => {
    const message = err instanceof ApiError ? err.message : fallback || String(err)
    setError(message)
  }, [])

  // --- initial config load -------------------------------------------------
  useEffect(() => {
    api
      .getConfig()
      .then((remote) => setConfig((c) => ({ ...c, ...remote })))
      .catch(() => {
        /* backend not reachable yet - keep local defaults, user can still play */
      })
  }, [])

  // --- config updates --------------------------------------------------------
  const updateConfig = useCallback(
    (patch) => {
      const previous = configRef.current
      setConfig((c) => ({ ...c, ...patch })) // optimistic
      api.updateConfig(patch).catch((err) => {
        setConfig(previous) // revert
        reportError(err, "Couldn't save that change")
      })
    },
    [reportError]
  )

  const applyContext = useCallback(
    (contextId) => {
      const preset = CONTEXTS[contextId]
      if (!preset) return
      updateConfig({ context: contextId, ...preset.weights })
    },
    [updateConfig]
  )

  const toggleHost = useCallback(
    (hostId) => {
      const active = configRef.current.active_hosts || []
      const isActive = active.includes(hostId)
      let nextActive
      if (isActive) {
        nextActive = active.filter((h) => h !== hostId)
        if (nextActive.length === 0) nextActive = [hostId] // always keep at least one on
      } else {
        nextActive = [...active, hostId]
      }
      const nextPersonality = isActive
        ? nextActive[nextActive.length - 1]
        : hostId // the one just turned on becomes the active generating voice
      updateConfig({ active_hosts: nextActive, host_personality: nextPersonality })
    },
    [updateConfig]
  )

  // --- music queue -----------------------------------------------------------
  const loadMusicQueue = useCallback(async () => {
    try {
      // Don't assume library key "1" is the music library - it varies per
      // Plex server (confirmed live: this deploy's Music library is key
      // "3"). Ask Plex which section is actually type: "music".
      const { libraries } = await api.getPlexLibraries()
      const musicLibrary = (libraries || []).find((lib) => lib.type === 'music')
      if (!musicLibrary) {
        reportError(null, 'No music library found in Plex')
        return []
      }

      const res = await api.getPlexTracks(musicLibrary.key, 50)
      const tracks = (res.tracks || []).filter((t) => t.stream_url)
      // shuffle
      for (let i = tracks.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[tracks[i], tracks[j]] = [tracks[j], tracks[i]]
      }
      musicQueueRef.current = tracks
      musicIndexRef.current = 0
      return tracks
    } catch (err) {
      reportError(err, "Couldn't load your music library")
      return []
    }
  }, [reportError])

  const playNextTrack = useCallback(() => {
    const queue = musicQueueRef.current
    if (!queue.length || !musicAudioRef.current) return
    const track = queue[musicIndexRef.current % queue.length]
    musicIndexRef.current += 1
    setNowPlayingTrack(track)
    musicAudioRef.current.src = api.audioUrl(track.stream_url)
    musicAudioRef.current.volume = volume
    musicAudioRef.current.play().catch(() => {
      /* autoplay may be blocked until a user gesture - Play button click counts */
    })
  }, [volume])

  // --- host segment generation & playback ------------------------------------
  const playSegmentAudio = useCallback((audioUrl, onDone) => {
    const el = segmentAudioRef.current
    if (!el || !audioUrl) {
      onDone()
      return
    }
    el.src = api.audioUrl(audioUrl)
    el.volume = volume
    el.onended = onDone
    el.play().catch(onDone)
  }, [volume])

  const duckMusic = useCallback((ducked) => {
    if (!musicAudioRef.current) return
    musicAudioRef.current.volume = ducked ? volume * DUCK_VOLUME_SCALE : volume
  }, [volume])

  const runSegment = useCallback(
    async (context, topic) => {
      setIsGenerating(true)
      try {
        const result = await api.generateSegment(context, topic)
        setCurrentSegment(result)
        setRecentTalk((prev) => [result, ...prev].slice(0, 20))

        duckMusic(true)
        clearTimeout(segmentTimeoutRef.current)

        const revert = () => {
          duckMusic(false)
          setCurrentSegment(null)
        }
        // Always revert after SEGMENT_MAX_DISPLAY_MS at the latest, even
        // if audio plays longer or shorter, or there's no audio at all.
        segmentTimeoutRef.current = setTimeout(revert, SEGMENT_MAX_DISPLAY_MS)
        if (result.audio_available) {
          playSegmentAudio(result.audio_url, () => {
            clearTimeout(segmentTimeoutRef.current)
            revert()
          })
        }
      } catch (err) {
        reportError(err, "Couldn't generate that segment")
      } finally {
        setIsGenerating(false)
      }
    },
    [duckMusic, playSegmentAudio, reportError]
  )

  const requestSegment = useCallback(
    (context) => {
      if (!isPlaying || isGenerating) return
      runSegment(context)
    },
    [isPlaying, isGenerating, runSegment]
  )

  // --- the "live station" tick loop ------------------------------------------
  const tick = useCallback(async () => {
    const cfg = configRef.current
    const pick = weightedPick({ ad: cfg.ad_weight, news: cfg.news_weight })
    if (!pick || isGenerating) return

    if (pick === 'ad') {
      runSegment('ad_lib')
      return
    }

    // news: pull a headline from enabled sources to hand the host a topic
    try {
      const res = await api.getNewsHeadlines(undefined, 5)
      const headlines = res.headlines || []
      const headline = headlines[Math.floor(Math.random() * headlines.length)]
      runSegment('news_banter', headline ? headline.title : undefined)
    } catch {
      runSegment('transition') // news unavailable this tick, fall back
    }
  }, [isGenerating, runSegment])

  const play = useCallback(async () => {
    setError(null)

    // Browsers only allow audio.play() to succeed without a rejected
    // promise when it's called synchronously within a real user gesture
    // (this click handler) or shortly after. Everything below this point
    // is async (loading the music queue, generating the intro segment),
    // which loses that "user activation" context - a .play() call after
    // an await gets silently blocked by autoplay policy, which is
    // exactly why neither music nor generated segments were audible
    // (confirmed live: no errors shown, just silence).
    //
    // The fix: call .play() on both elements synchronously, right here,
    // before any await. They have no src yet so this immediately rejects
    // - that's fine and expected, we just need the *attempt* to happen
    // inside the gesture to "unlock" each element for this session, so
    // the real .play() calls later (after the async work below) are
    // allowed through.
    musicAudioRef.current?.play().catch(() => {})
    segmentAudioRef.current?.play().catch(() => {})

    if (!musicQueueRef.current.length) {
      const tracks = await loadMusicQueue()
      if (!tracks.length) {
        reportError(null, 'No music available to play - check Plex is connected.')
        return
      }
    }
    setIsPlaying(true)
    playNextTrack()
    runSegment('intro')
    tickTimerRef.current = setInterval(tick, TICK_MS)
  }, [loadMusicQueue, playNextTrack, runSegment, tick, reportError])

  const pause = useCallback(() => {
    setIsPlaying(false)
    musicAudioRef.current?.pause()
    segmentAudioRef.current?.pause()
    clearInterval(tickTimerRef.current)
    clearTimeout(segmentTimeoutRef.current)
  }, [])

  const togglePlayback = useCallback(() => {
    if (isPlaying) pause()
    else play()
  }, [isPlaying, pause, play])

  // music auto-advance
  useEffect(() => {
    const el = musicAudioRef.current
    if (!el) return
    const handleEnded = () => playNextTrack()
    el.addEventListener('ended', handleEnded)
    return () => el.removeEventListener('ended', handleEnded)
  }, [playNextTrack])

  // Surface real playback failures instead of failing silently - a prior
  // version had no error handling here at all, so a broken stream URL (or
  // an autoplay-policy block) just looked like "nothing happens," with no
  // way to tell what was actually wrong from the UI.
  useEffect(() => {
    const musicEl = musicAudioRef.current
    const segmentEl = segmentAudioRef.current
    if (!musicEl || !segmentEl) return

    const onMusicError = () => {
      if (!musicEl.src) return // no src set yet (e.g. the priming play() on Play) - not a real failure
      reportError(null, "Couldn't play that track - skipping to the next one")
      playNextTrack()
    }
    const onSegmentError = () => {
      if (!segmentEl.src) return
      reportError(null, "Couldn't play the generated audio segment")
    }

    musicEl.addEventListener('error', onMusicError)
    segmentEl.addEventListener('error', onSegmentError)
    return () => {
      musicEl.removeEventListener('error', onMusicError)
      segmentEl.removeEventListener('error', onSegmentError)
    }
  }, [playNextTrack, reportError])

  // Media Session API - lock screen / notification controls
  useEffect(() => {
    if (!('mediaSession' in navigator)) return
    navigator.mediaSession.metadata = new window.MediaMetadata({
      title: currentSegment ? `${currentSegment.host}: ${currentSegment.context || 'On Air'}` : nowPlayingTrack?.title || 'RadioMe Live',
      artist: currentSegment ? 'RadioMe Live' : nowPlayingTrack?.artist || '',
      album: nowPlayingTrack?.album || 'RadioMe Live'
    })
    navigator.mediaSession.setActionHandler('play', play)
    navigator.mediaSession.setActionHandler('pause', pause)
    navigator.mediaSession.setActionHandler('nexttrack', playNextTrack)
  }, [currentSegment, nowPlayingTrack, play, pause, playNextTrack])

  // theme application
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    return () => {
      clearInterval(tickTimerRef.current)
      clearTimeout(segmentTimeoutRef.current)
    }
  }, [])

  return {
    config,
    updateConfig,
    applyContext,
    toggleHost,
    isPlaying,
    isGenerating,
    togglePlayback,
    currentSegment,
    nowPlayingTrack,
    recentTalk,
    requestSegment,
    error,
    dismissError: () => setError(null),
    retryLoadTracks: loadMusicQueue,
    volume,
    setVolume: setVolumeState,
    theme,
    setTheme,
    musicAudioRef,
    segmentAudioRef
  }
}
