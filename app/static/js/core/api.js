/**
 * Centralized API client for MAM Audiobook Finder
 * All backend API calls go through this module
 */

/**
 * Get auth token from localStorage
 * @returns {string|null}
 */
function getAuthToken() {
  return localStorage.getItem('abs_token')
}

/**
 * Build headers with auth token if available
 * @param {Object} extra - Additional headers to include
 * @returns {Object}
 */
function buildHeaders(extra = {}) {
  const headers = { ...extra }
  const token = getAuthToken()
  if (token) {
    headers['X-ABS-Token'] = token
  }
  return headers
}

/**
 * API client with methods for all backend endpoints
 */
export const api = {
  /**
   * Generic GET request helper
   * @param {string} url - URL to fetch
   * @returns {Promise<Object>}
   */
  async get(url) {
    const r = await fetch(url, {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  /**
   * Health check endpoint
   * @returns {Promise<{ok: boolean}>}
   */
  async health() {
    const r = await fetch('/health', {
      headers: buildHeaders()
    });
    return r.json();
  },

  /**
   * Get application configuration
   * @returns {Promise<Object>}
   */
  async getConfig() {
    const r = await fetch('/config', {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  /**
   * Search MAM for audiobooks
   * @param {Object} payload - Search parameters
   * @param {Object} payload.tor - Torrent search criteria
   * @param {string} payload.tor.text - Search query
   * @param {string} payload.tor.sortType - Sort type
   * @param {number} payload.perpage - Results per page
   * @returns {Promise<{results: Array}>}
   */
  async search(payload) {
    const resp = await fetch('/search', {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Add torrent to qBittorrent
   * @param {Object} params - Torrent parameters
   * @returns {Promise<Object>}
   */
  async addTorrent(params) {
    const resp = await fetch('/add', {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(params)
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * Get torrent history
   * @returns {Promise<{items: Array}>}
   */
  async getHistory() {
    const r = await fetch('/api/history', {
      cache: 'no-cache',
      headers: buildHeaders({
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      })
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    console.log('[API] History response:', data.items?.length || 0, 'items');
    if (data.items?.length > 0) {
      console.log('[API] Sample item status:', {
        title: data.items[0].title,
        qb_status: data.items[0].qb_status,
        qb_status_color: data.items[0].qb_status_color,
        qb_hash: data.items[0].qb_hash
      });
    }
    return data;
  },

  /**
   * Delete history item
   * @param {number|string} id - History item ID
   * @returns {Promise<Object>}
   */
  async deleteHistoryItem(id) {
    const resp = await fetch(`/api/history/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: buildHeaders()
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Manually trigger verification for a history item
   * @param {number|string} id - History item ID
   * @returns {Promise<{ok: boolean, verification: Object}>}
   */
  async verifyHistoryItem(id) {
    const resp = await fetch(`/api/history/${encodeURIComponent(id)}/verify`, {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' })
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * Get completed torrents from qBittorrent
   * @returns {Promise<{items: Array}>}
   */
  async getCompletedTorrents() {
    const r = await fetch('/qb/torrents', {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  /**
   * Get torrent file tree with multi-disc detection
   * @param {string} hash - Torrent hash
   * @returns {Promise<Object>}
   */
  async getTorrentTree(hash) {
    const r = await fetch(`/qb/torrent/${encodeURIComponent(hash)}/tree`, {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  /**
   * Import torrent to library
   * @param {Object} params - Import parameters
   * @param {string} params.author - Author name
   * @param {string} params.title - Book title
   * @param {string} params.hash - Torrent hash
   * @param {number} params.history_id - History item ID
   * @param {boolean} params.flatten - Whether to flatten multi-disc structure
   * @returns {Promise<Object>}
   */
  async importTorrent(params) {
    const r = await fetch('/import', {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(params)
    });
    if (!r.ok) {
      let msg = `HTTP ${r.status}`;
      try {
        const j = await r.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return r.json();
  },

  /**
   * Get application logs
   * @param {Object} params - Log query parameters
   * @param {number} params.lines - Number of lines to retrieve
   * @param {string} params.level - Log level filter (INFO, WARNING, ERROR)
   * @returns {Promise<{ok: boolean, logs: Array<string>}>}
   */
  async getLogs(params) {
    const queryParams = new URLSearchParams({
      lines: params.lines.toString(),
      level: params.level || ''
    });
    const resp = await fetch(`/api/logs?${queryParams}`, {
      headers: buildHeaders()
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Fetch cover image for an audiobook
   * @param {Object} params - Cover fetch parameters
   * @param {string} params.mam_id - MAM torrent ID
   * @param {string} params.title - Book title
   * @param {string} params.author - Author name
   * @param {string} params.max_retries - Maximum retry attempts
   * @returns {Promise<{cover_url?: string, item_id?: string, error?: string}>}
   */
  async fetchCover(params) {
    const queryParams = new URLSearchParams({
      mam_id: params.mam_id,
      title: params.title || '',
      author: params.author || '',
      max_retries: params.max_retries || '2'
    });
    const resp = await fetch(`/api/covers/fetch?${queryParams}`, {
      headers: buildHeaders()
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Get showcase audiobooks (grouped by title)
   * @param {Object} params - Showcase query parameters
   * @param {string} params.query - Search query
   * @param {number} params.limit - Result limit
   * @returns {Promise<{groups: Array, total_groups: number, total_results: number}>}
   */
  async getShowcase(params) {
    const queryParams = new URLSearchParams({
      query: params.query || '',
      limit: params.limit.toString()
    });
    const resp = await fetch(`/api/showcase?${queryParams}`, {
      headers: buildHeaders()
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Search for series on Hardcover by title and/or author
   * @param {Object} params - Series search parameters
   * @param {string} params.title - Book title to search
   * @param {string} params.author - Author name (optional)
   * @param {string} params.normalized_title - Normalized title (optional)
   * @param {number} params.limit - Result limit (optional, uses server default if not provided)
   * @returns {Promise<{query: Object, hardcover_series: Array, cached: boolean, timestamp: string}>}
   */
  async searchSeries(params) {
    const resp = await fetch('/api/series/search', {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        title: params.title,
        author: params.author || '',
        normalized_title: params.normalized_title || null,
        limit: params.limit || undefined
      })
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * Get books in a series from Hardcover with progressive enrichment support.
   * @param {number} seriesId - Hardcover series ID
   * @param {Object} options - Query options
   * @param {string} options.enrich_mode - Enrichment mode: "immediate" (return basic data, enrich in background),
   *                                       "wait" (wait for full enrichment), or "status" (check enrichment progress)
   *                                       Default: "immediate" for fast initial load
   * @param {boolean} options.showAllEditions - If true, return all editions including non-English versions.
   *                                            If false (default), return only canonical English primary editions.
   *                                            Each book will have an 'is_canonical' field.
   * @param {number} options.per_page - Books per page (default: 5) [deprecated, pagination not implemented]
   * @param {number} options.page - Page number, 1-indexed (default: 1) [deprecated, pagination not implemented]
   * @returns {Promise<{series_id: number, series_name: string, author_name: string, books: Array, enrichment_status: string, enrichment_progress: Object, total: number, timestamp: string}>}
   */
  async getSeriesBooks(seriesId, options = {}) {
    const { per_page = 5, page = 1, enrich_mode = 'immediate', showAllEditions = false } = options;

    const params = new URLSearchParams({
      enrich_mode: enrich_mode,
      show_all_editions: showAllEditions ? 'true' : 'false'
    });

    // Keep per_page and page for backward compatibility (though backend ignores them currently)
    if (per_page) params.append('per_page', String(per_page));
    if (page) params.append('page', String(page));

    const resp = await fetch(`/api/series/${seriesId}/books?${params}`, {
      headers: buildHeaders()
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * Fetch audiobook metadata for specific books in a series (or all books).
   * This allows on-demand fetching of audiobook metadata from Hardcover without blocking the initial series load.
   * @param {number} seriesId - Hardcover series ID
   * @param {Array<number>|null} bookIndices - List of book positions to enrich, or null/[] for all books
   * @returns {Promise<{series_id: number, enriched_count: number, books: Array, errors: Array}>}
   */
  async fetchSeriesAudioMetadata(seriesId, bookIndices = null) {
    const resp = await fetch(`/api/series/${seriesId}/books/fetch-audio`, {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ book_indices: bookIndices })
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * On-demand metadata enrichment for detail views.
   * Calls provider APIs in parallel to fetch enhanced metadata including descriptions.
   * Only used when user explicitly opens a detail view.
   *
   * @param {Object} params - Enrichment parameters
   * @param {string} params.title - Book title (required)
   * @param {string} params.author - Author name (optional)
   * @param {string} params.mam_id - MAM torrent ID (optional)
   * @returns {Promise<{description: string, cover: string, asin?: string, isbn?: string, publisher?: string, narrator?: string, series: Array, rating?: number, source: string}>}
   */
  async enrichMetadata(params) {
    const resp = await fetch('/api/covers/enrich', {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        title: params.title,
        author: params.author || '',
        mam_id: params.mam_id || ''
      })
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  // ======================== Settings API ========================

  /**
   * Get all application settings
   * @returns {Promise<Object>}
   */
  async getSettings() {
    const r = await fetch('/api/settings', {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  },

  /**
   * Update application settings
   * @param {Object} settings - Settings to update
   * @param {boolean} settings.auto_import_enabled - Enable auto-import
   * @param {boolean} settings.auto_import_flatten - Flatten during auto-import
   * @param {number} settings.auto_import_poll_interval - Poll interval in seconds
   * @returns {Promise<{ok: boolean, updated: Array}>}
   */
  async updateSettings(settings) {
    const resp = await fetch('/api/settings', {
      method: 'PUT',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(settings)
    });
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const j = await resp.json();
        if (j?.detail) msg += ` — ${j.detail}`;
      } catch {}
      throw new Error(msg);
    }
    return resp.json();
  },

  /**
   * Reset all settings to defaults
   * @returns {Promise<{ok: boolean}>}
   */
  async resetSettings() {
    const resp = await fetch('/api/settings/reset', {
      method: 'POST',
      headers: buildHeaders()
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  },

  /**
   * Get auto-import service status
   * @returns {Promise<Object>}
   */
  async getAutoImportStatus() {
    const r = await fetch('/api/settings/auto-import/status', {
      headers: buildHeaders()
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }
};
