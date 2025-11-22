/**
 * useCover Composable
 * Enhanced composable for fetching cover URLs from the backend with in-memory caching
 * Used with NaiveUI's n-image component which handles lazy loading
 */

import { ref } from 'vue'
import { useApi } from '../useApi.js'

// Cache configuration
const CACHE_TTL = 5 * 60 * 1000  // 5 minutes in milliseconds
const MAX_CACHE_SIZE = 100       // Maximum number of cached covers

/**
 * Enhanced cover cache with TTL and LRU eviction
 */
const coverCache = new Map()

/**
 * Get cache key from MAM ID and title
 */
function getCacheKey(mamId, title) {
  return `${mamId}-${title}`
}

/**
 * Get cached cover data with TTL check
 */
function getCached(key) {
  const cached = coverCache.get(key)
  if (!cached) return null

  // Check if cache entry has expired
  const now = Date.now()
  if (now - cached.timestamp > CACHE_TTL) {
    coverCache.delete(key)
    return null
  }

  return cached.data
}

/**
 * Set cache entry with LRU eviction
 */
function setCache(key, data) {
  // LRU eviction: Remove oldest entry if cache is full
  if (coverCache.size >= MAX_CACHE_SIZE) {
    const firstKey = coverCache.keys().next().value
    coverCache.delete(firstKey)
  }

  coverCache.set(key, {
    data,
    timestamp: Date.now()
  })
}

/**
 * Clear all cached covers
 */
export function clearCoverCache() {
  coverCache.clear()
}

/**
 * Create a cover fetcher for a specific item with caching
 * @param {Object} params - Cover parameters
 * @param {string} params.mamId - MAM torrent ID
 * @param {string} params.title - Book title
 * @param {string} params.author - Author name
 * @param {boolean} params.enableCache - Enable caching (default: true)
 * @returns {Object} Cover state and fetch functions
 */
export function useCover({ mamId, title, author, enableCache = true }) {
  const api = useApi()
  const coverUrl = ref('')
  const loading = ref(false)
  const error = ref('')

  const cacheKey = getCacheKey(mamId, title)

  // Check cache on initialization if enabled
  if (enableCache) {
    const cached = getCached(cacheKey)
    if (cached) {
      coverUrl.value = cached.coverUrl
      loading.value = false
    }
  }

  /**
   * Fetch cover from backend (with optional cache bypass)
   */
  const fetchCover = async (bypassCache = false) => {
    if (!mamId || !title) {
      error.value = 'Missing required info'
      return
    }

    // Return cached value if available and not bypassing
    if (enableCache && !bypassCache) {
      const cached = getCached(cacheKey)
      if (cached) {
        coverUrl.value = cached.coverUrl
        return
      }
    }

    loading.value = true
    error.value = ''

    try {
      const data = await api.fetchCover({
        mam_id: mamId,
        title: title,
        author: author || '',
        max_retries: '2'
      })

      if (data.cover_url) {
        coverUrl.value = data.cover_url

        // Cache the result if caching is enabled
        if (enableCache) {
          setCache(cacheKey, { coverUrl: data.cover_url })
        }
      } else {
        error.value = data.error || 'No cover found'
      }
    } catch (e) {
      console.error('Cover fetch error:', e)
      error.value = 'Failed to load cover'
    } finally {
      loading.value = false
    }
  }

  /**
   * Force refetch (bypass cache)
   */
  const refetch = async () => {
    await fetchCover(true)
  }

  return {
    coverUrl,
    loading,
    error,
    fetchCover,
    refetch
  }
}

/**
 * Get or fetch a cover URL with caching (helper function)
 * @param {string} mamId - MAM torrent ID
 * @param {string} title - Book title
 * @param {string} author - Author name
 * @returns {Promise<string>} Cover URL or empty string
 */
export async function getCoverUrl(mamId, title, author) {
  const cacheKey = getCacheKey(mamId, title)

  // Check cache first
  const cached = getCached(cacheKey)
  if (cached) {
    return cached.coverUrl
  }

  // Fetch from API using useCover (which will cache automatically)
  const { coverUrl, fetchCover } = useCover({ mamId, title, author, enableCache: true })
  await fetchCover()

  return coverUrl.value
}
