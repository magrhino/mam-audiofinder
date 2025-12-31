/**
 * Vue Composable for API access
 * Provides a frontend-native API client with centralized ABS auth.
 */

import { useAuth } from '@composables/useAuth'

/**
 * Build request headers, injecting `X-ABS-Token` when available.
 */
function buildHeaders(extra = {}) {
  const headers = { ...extra }
  const { getToken } = useAuth()
  const token = getToken()
  if (token) {
    headers['X-ABS-Token'] = token
  }
  return headers
}

async function safeJson(resp) {
  try {
    return await resp.json()
  } catch {
    return null
  }
}

async function errorMessage(resp) {
  const data = await safeJson(resp)
  const detail = data?.detail || data?.error
  if (detail) return `HTTP ${resp.status} — ${detail}`
  return `HTTP ${resp.status}`
}

async function requestJson(url, options = {}) {
  const {
    method = 'GET',
    headers: extraHeaders = {},
    body,
    cache,
  } = options

  const init = {
    method,
    cache,
    headers: buildHeaders(extraHeaders)
  }

  if (body !== undefined) {
    init.body = JSON.stringify(body)
    init.headers = buildHeaders({
      'Content-Type': 'application/json',
      ...extraHeaders
    })
  }

  const resp = await fetch(url, init)
  if (!resp.ok) {
    throw new Error(await errorMessage(resp))
  }

  return resp.json()
}

/**
 * API client with methods for all backend endpoints.
 */
const api = {
  // Generic helpers
  get(url) {
    return requestJson(url)
  },
  post(url, body) {
    return requestJson(url, { method: 'POST', body })
  },

  // Health / config
  async health() {
    const resp = await fetch('/health', { headers: buildHeaders() })
    return resp.json()
  },
  getConfig() {
    return requestJson('/config')
  },

  // MAM search
  search(payload) {
    return requestJson('/search', { method: 'POST', body: payload })
  },

  // qBittorrent
  addTorrent(params) {
    return requestJson('/add', { method: 'POST', body: params })
  },
  getCompletedTorrents() {
    return requestJson('/qb/torrents')
  },
  getTorrentTree(hash) {
    return requestJson(`/qb/torrent/${encodeURIComponent(hash)}/tree`)
  },

  // Import
  importTorrent(params) {
    return requestJson('/import', { method: 'POST', body: params })
  },

  // History
  getHistory() {
    return requestJson('/api/history', {
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    })
  },
  deleteHistoryItem(id) {
    return requestJson(`/api/history/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  verifyHistoryItem(id) {
    return requestJson(`/api/history/${encodeURIComponent(id)}/verify`, { method: 'POST' })
  },

  // Logs
  getLogs(params) {
    const queryParams = new URLSearchParams({
      lines: params.lines.toString(),
      level: params.level || ''
    })
    return requestJson(`/api/logs?${queryParams}`)
  },

  // Covers
  fetchCover(params) {
    const queryParams = new URLSearchParams({
      mam_id: params.mam_id,
      title: params.title || '',
      author: params.author || '',
      max_retries: params.max_retries || '2'
    })
    return requestJson(`/api/covers/fetch?${queryParams}`)
  },
  enrichMetadata(params) {
    return requestJson('/api/covers/enrich', {
      method: 'POST',
      body: {
        title: params.title,
        author: params.author || '',
        mam_id: params.mam_id || ''
      }
    })
  },

  // Showcase
  getShowcase(params) {
    const queryParams = new URLSearchParams({
      query: params.query || '',
      limit: params.limit.toString()
    })
    return requestJson(`/api/showcase?${queryParams}`)
  },

  // Hardcover series
  searchSeries(params) {
    return requestJson('/api/series/search', {
      method: 'POST',
      body: {
        title: params.title,
        author: params.author || '',
        normalized_title: params.normalized_title || null,
        limit: params.limit || undefined
      }
    })
  },
  getSeriesBooks(seriesId, options = {}) {
    const {
      per_page = 5,
      page = 1,
      enrich_mode = 'immediate',
      showAllEditions = false,
    } = options

    const queryParams = new URLSearchParams({
      enrich_mode,
      show_all_editions: showAllEditions ? 'true' : 'false'
    })
    if (per_page) queryParams.append('per_page', String(per_page))
    if (page) queryParams.append('page', String(page))

    return requestJson(`/api/series/${encodeURIComponent(seriesId)}/books?${queryParams}`)
  },
  fetchSeriesAudioMetadata(seriesId, bookIndices = null) {
    return requestJson(`/api/series/${encodeURIComponent(seriesId)}/books/fetch-audio`, {
      method: 'POST',
      body: { book_indices: bookIndices }
    })
  },

  // Settings
  getSettings() {
    return requestJson('/api/settings')
  },
  updateSettings(settings) {
    return requestJson('/api/settings', { method: 'PUT', body: settings })
  },
  resetSettings() {
    return requestJson('/api/settings/reset', { method: 'POST' })
  },
  getAutoImportStatus() {
    return requestJson('/api/settings/auto-import/status')
  }
}

/**
 * Composable for accessing the API client.
 */
export function useApi() {
  return api
}
