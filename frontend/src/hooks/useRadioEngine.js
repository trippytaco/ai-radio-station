import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import { CONTEXTS } from '../constants/contexts'
import { useLocalStorage } from './useLocalStorage'

const SEGMENT_MAX_DISPLAY_MS = 9000
const DUCK_VOLUME_SCALE = 0.15
// Auto-generated host talk (ad/news, not manual requests) only fires near
// a track's intro or outro - never mid-song. A fixed interval timer used
// to fire regardless of playback position, which is exactly what made it
// feel wrong ("host talking over the middle of a song like a real DJ
// wouldn't"). Very short tracks (shorter than both windows combined)
// only get one shot, via the intro window.
const INTRO_WINDOW_SEC = 12
const OUTRO_WINDOW_SEC = 12

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

// Product categories to steer ad_lib generation - cycled through without
// repeats (until the pool is exhausted, then reshuffled) so ads actually
// vary instead of the model producing similarly-generic fake products
// every time from an identical, unvaried prompt.
const AD_THEMES = [
  'kitchen gadgets', 'fitness equipment', 'skincare', 'pet products',
  'financial services', 'cleaning products', 'tech gadgets', 'travel',
  'subscription boxes', 'home security', 'car care', 'diet supplements',
  'dating apps', 'mattresses', 'energy drinks', 'insurance'
]

function shuffled(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
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
  const [playHistory, setPlayHistory] = useState([]) // tracks this station has actually played
  const [error, setError] = useState(null)
  const [volume, setVolumeState] = useLocalStorage('radiome:volume', 0.8)
  const [theme, setTheme] = useLocalStorage('radiome:theme', 'system')

  const musicAudioRef = useRef(null)
  const segmentAudioRef = useRef(null)
  const musicQueueRef = useRef([])
  const musicIndexRef = useRef(0)
  const segmentTimeoutRef = useRef(null)
  const introTriggeredRef = useRef(false) // has this track's intro window already been used
  const outroTriggeredRef = useRef(false)
  const adThemeQueueRef = useRef(shuffled(AD_THEMES)) // pop from this; reshuffle when empty
  const usedHeadlinesRef = useRef(new Set()) // headline titles already used this session
  const configRef = useRef(config)
  configRef.current = config
  // True from the moment a segment starts generating until its audio (or
  // the display fallback) actually finishes - not the same as
  // isGenerating, which only covers the API call. A tick or a manual
  // request arriving while this is true must never cut off what's
  // currently playing (mix/host/context changes already only affect
  // future segments and don't need this - see updateConfig).
  const segmentActiveRef = useRef(false)
  const pendingRequestRef = useRef(null) // {context, topic} | null - at most one queued
  const [isSegmentQueued, setIsSegmentQueued] = useState(false)
  // isPlaying (React state) is only current at render time - runSegment
  // needs to check the *live* value after an await, when a stale closure
  // over isPlaying could still say true even though pause() ran in the
  // meantime. This ref is kept in sync everywhere setIsPlaying is called.
  const isPlayingRef = useRef(false)

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
    setPlayHistory((prev) => [{ ...track, played_at: new Date().toISOString() }, ...prev].slice(0, 20))
    musicAudioRef.current.src = api.audioUrl(track.stream_url)
    musicAudioRef.current.volume = volume
    introTriggeredRef.current = false
    outroTriggeredRef.current = false
    musicAudioRef.current.play().catch(() => {
      /* autoplay may be blocked until a user gesture - Play button click counts */
    })
  }, [volume])

  const skipTrack = useCallback(() => {
    if (!isPlaying) return
    playNextTrack()
  }, [isPlaying, playNextTrack])

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
      // Never start a new segment over one that's still active (generating
      // or its audio still playing) - queue it instead. This is what
      // actually keeps the illusion of a live station intact: a request
      // or an auto-tick can decide *what* plays next, but never *when*
      // the current thing gets cut off.
      if (segmentActiveRef.current) {
        pendingRequestRef.current = { context, topic }
        setIsSegmentQueued(true)
        return
      }

      segmentActiveRef.current = true
      setIsGenerating(true)
      try {
        const result = await api.generateSegment(context, topic)

        // The station may have been paused while this generation was in
        // flight (a real async gap) - confirmed live: pause() correctly
        // stopped whatever audio was already playing, but a segment still
        // being *generated* at that moment ignored it and started playing
        // once the API call resolved anyway. isPlaying (state) can't be
        // trusted here - this closure captured whatever it was when
        // runSegment was called, not the current value - hence the ref.
        if (!isPlayingRef.current) {
          segmentActiveRef.current = false
          pendingRequestRef.current = null
          setIsSegmentQueued(false)
          return
        }

        setCurrentSegment(result)
        setRecentTalk((prev) => [result, ...prev].slice(0, 20))

        duckMusic(true)
        clearTimeout(segmentTimeoutRef.current)

        const revert = () => {
          duckMusic(false)
          setCurrentSegment(null)
          segmentActiveRef.current = false

          // A request or tick came in while this segment was playing -
          // run it now that it's actually safe to.
          const pending = pendingRequestRef.current
          if (pending) {
            pendingRequestRef.current = null
            setIsSegmentQueued(false)
            runSegment(pending.context, pending.topic)
          }
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
        segmentActiveRef.current = false
      } finally {
        setIsGenerating(false)
      }
    },
    [duckMusic, playSegmentAudio, reportError]
  )

  // Pops one theme off the shuffled queue (reshuffling when exhausted) so
  // ad_lib gets a fresh, non-repeating category each time within a cycle.
  const nextAdTheme = useCallback(() => {
    if (adThemeQueueRef.current.length === 0) {
      adThemeQueueRef.current = shuffled(AD_THEMES)
    }
    return adThemeQueueRef.current.pop()
  }, [])

  const requestSegment = useCallback(
    (context) => {
      if (!isPlaying) return
      runSegment(context, context === 'ad_lib' ? nextAdTheme() : undefined)
    },
    [isPlaying, runSegment, nextAdTheme]
  )

  // --- auto-generated host talk, gated to a track's intro/outro only ---------
  const attemptAutoSegment = useCallback(async () => {
    // An auto-trigger shouldn't queue itself up behind a segment that's
    // already active - it'll get another chance at the next track's
    // intro/outro. Queueing every attempt would pile auto-generated talk
    // up behind things the listener never asked for.
    if (segmentActiveRef.current) return

    const cfg = configRef.current
    // music_weight has to be in this roll too, not just ad vs news against
    // each other - otherwise every single intro/outro window guarantees
    // a talk segment regardless of the Music slider, which is exactly
    // what made it feel like it was constantly talking over the music
    // (confirmed live: every track's start and end triggered talk, with
    // no "just let it play" outcome ever possible).
    const pick = weightedPick({ music: cfg.music_weight, ad: cfg.ad_weight, news: cfg.news_weight })
    if (!pick || pick === 'music') return

    if (pick === 'ad') {
      runSegment('ad_lib', nextAdTheme())
      return
    }

    // news: pull a headline from enabled sources, skipping ones already
    // used this session so the same story doesn't get read out twice.
    try {
      const res = await api.getNewsHeadlines(undefined, 20)
      const headlines = res.headlines || []
      const fresh = headlines.filter((h) => h.title && !usedHeadlinesRef.current.has(h.title))
      if (fresh.length === 0) {
        runSegment('transition') // nothing unused right now, don't repeat - just transition
        return
      }
      const headline = fresh[Math.floor(Math.random() * fresh.length)]
      usedHeadlinesRef.current.add(headline.title)
      runSegment('news_banter', headline.title)
    } catch {
      runSegment('transition') // news unavailable this attempt, fall back
    }
  }, [runSegment, nextAdTheme])

  // Fires attemptAutoSegment at most once per track, only while inside the
  // first/last INTRO_WINDOW_SEC/OUTRO_WINDOW_SEC of it - never mid-song.
  // Whether anything actually plays is still gated by attemptAutoSegment's
  // own weighted roll (ad_weight/news_weight), so most windows pass silently.
  useEffect(() => {
    const el = musicAudioRef.current
    if (!el) return

    const onTimeUpdate = () => {
      if (!isPlaying) return
      const { currentTime, duration } = el
      if (!duration || Number.isNaN(duration)) return

      if (currentTime <= INTRO_WINDOW_SEC && !introTriggeredRef.current) {
        introTriggeredRef.current = true
        attemptAutoSegment()
      } else if (
        duration - currentTime <= OUTRO_WINDOW_SEC &&
        duration > INTRO_WINDOW_SEC + OUTRO_WINDOW_SEC && // short tracks: intro window only, avoid an immediate double-fire
        !outroTriggeredRef.current
      ) {
        outroTriggeredRef.current = true
        attemptAutoSegment()
      }
    }

    el.addEventListener('timeupdate', onTimeUpdate)
    return () => el.removeEventListener('timeupdate', onTimeUpdate)
  }, [isPlaying, attemptAutoSegment])

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
    isPlayingRef.current = true
    setIsPlaying(true)
    playNextTrack()
    // playNextTrack() just reset introTriggeredRef to false for this track;
    // mark it used since we're explicitly opening with an intro segment
    // here, so the timeupdate-driven window check doesn't also fire one
    // moments later for the same track.
    introTriggeredRef.current = true
    runSegment('intro')
  }, [loadMusicQueue, playNextTrack, runSegment, reportError])

  const pause = useCallback(() => {
    isPlayingRef.current = false
    setIsPlaying(false)
    musicAudioRef.current?.pause()
    segmentAudioRef.current?.pause()
    clearTimeout(segmentTimeoutRef.current)
    segmentActiveRef.current = false
    pendingRequestRef.current = null
    setIsSegmentQueued(false)
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
    isSegmentQueued,
    togglePlayback,
    currentSegment,
    nowPlayingTrack,
    recentTalk,
    playHistory,
    requestSegment,
    skipTrack,
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
