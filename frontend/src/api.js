// Backend base URL. Set VITE_API_BASE at build time to point at a
// different backend; defaults to the live production API.
export const API_BASE = import.meta.env.VITE_API_BASE || 'https://radiome.orosz.cc'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { method = 'GET', params, body, timeoutMs = 30000 } = {}) {
  const url = new URL(API_BASE + path)
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

  getNewsHeadlines: (source, limit = 5) =>
    request('/news/headlines', { params: { source, limit } }).then((r) => r.json()),

  getTtsProviders: () => request('/tts/providers').then((r) => r.json()),
  switchTtsProvider: (provider) =>
    request('/tts/switch', { method: 'POST', params: { provider } }).then((r) => r.json()),

  audioUrl: (path) => (path ? API_BASE + path : null)
}

export { ApiError }
