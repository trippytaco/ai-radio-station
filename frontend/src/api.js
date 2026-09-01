// Backend base URL, relative or absolute. Set VITE_API_BASE at build time;
// defaults to /api (path-based routing on the same domain the frontend is
// served from - see nginx/reverse-proxy config, which strips /api before
// forwarding to the backend).
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { method = 'GET', params, body, timeoutMs = 30000 } = {}) {
  // Second arg resolves a relative API_BASE (e.g. "/api") against the
  // current page's origin; a full absolute API_BASE (e.g. in dev, or a
  // deploy without path-based routing) is used as-is - the base is only
  // consulted when the first argument isn't already absolute.
  const url = new URL(API_BASE + path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, value)
    }
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  let response
  try {
    response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new ApiError(`${path} timed out`, 0)
    }
    throw new ApiError(`Couldn't reach the station (${err.message})`, 0)
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {
      // body wasn't JSON, keep statusText
    }
    throw new ApiError(detail, response.status)
  }

  return response
}

export const api = {
  health: () => request('/health').then((r) => r.json()),

  getConfig: () => request('/config').then((r) => r.json()),
  updateConfig: (patch) =>
    request('/config', { method: 'POST', body: patch }).then((r) => r.json()),

  generateSegment: (context, topic) =>
    request('/generate/host-segment', { method: 'POST', params: { context, topic } }).then((r) =>
      r.json()
    ),

  getPlexLibraries: () => request('/plex/libraries').then((r) => r.json()),

  getPlexTracks: (libraryKey, limit = 50) =>
    request('/plex/tracks', { params: { library_key: libraryKey, limit } }).then((r) => r.json()),

  getRecentTracks: (limit = 10) =>
    request('/lastfm/recent', { params: { limit } }).then((r) => r.json()),

  getTopArtists: (period = '1month', limit = 20) =>
    request('/lastfm/top-artists', { params: { period, limit } }).then((r) => r.json()),

  // Both best-effort - callers should swallow errors from these rather
  // than surfacing them, a failed scrobble/now-playing update shouldn't
  // interrupt playback.
  updateNowPlaying: (artist, track, album) =>
    request('/lastfm/now-playing', { method: 'POST', params: { artist, track, album } }).then((r) => r.json()),
  scrobbleTrack: (artist, track, timestamp, album) =>
    request('/lastfm/scrobble', { method: 'POST', params: { artist, track, timestamp, album } }).then((r) => r.json()),

  getNewsHeadlines: (source, limit = 5) =>
    request('/news/headlines', { params: { source, limit } }).then((r) => r.json()),

  getTtsProviders: () => request('/tts/providers').then((r) => r.json()),
  switchTtsProvider: (provider) =>
    request('/tts/switch', { method: 'POST', params: { provider } }).then((r) => r.json()),

  audioUrl: (path) => (path ? API_BASE + path : null)
}

export { ApiError }
