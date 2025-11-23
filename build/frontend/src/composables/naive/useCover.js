/**
 * useCover Composable
 * Universal cover fetching composable with caching, lazy loading, and badge overlay support
 *
 * Features:
 * - In-memory cache with TTL and LRU eviction
 * - IntersectionObserver lazy loading support
 * - Backend cover_url passthrough (skip fetch if URL provided)
 * - Badge overlay metadata (library, audiobook, series indicators)
 */

import { ref, onUnmounted } from 'vue'
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
 * Create a cover fetcher for a specific item with caching and lazy loading
 * @param {Object} params - Cover parameters
 * @param {string} params.mamId - MAM torrent ID
 * @param {string} params.title - Book title
 * @param {string} params.author - Author name
 * @param {string} params.initialUrl - Optional backend-provided cover URL (bypasses fetch)
 * @param {boolean} params.enableCache - Enable caching (default: true)
 * @param {boolean} params.lazy - Enable lazy loading with IntersectionObserver (default: false)
 * @param {string} params.priority - Loading priority: 'high', 'normal', 'low' (default: 'normal')
 * @param {boolean} params.inLibrary - Book is in Audiobookshelf library (badge overlay)
 * @param {boolean} params.hasAudiobook - Audiobook format available (badge overlay)
 * @param {string|number} params.seriesNumber - Series number for badge overlay
 * @returns {Object} Cover state, fetch functions, and observer setup
 */
export function useCover({
  mamId,
  title,
  author,
  initialUrl = '',
  enableCache = true,
  lazy = false,
  priority = 'normal',
  inLibrary = false,
  hasAudiobook = null,
  seriesNumber = null
}) {
  const api = useApi()
  const coverUrl = ref('')
  const loading = ref(false)
  const error = ref('')
  const observer = ref(null)
  const observedElement = ref(null)

  const cacheKey = getCacheKey(mamId, title)

  // Backend cover_url passthrough - use provided URL without fetch
  if (initialUrl) {
    coverUrl.value = initialUrl
    loading.value = false
    // Cache the passthrough URL
    if (enableCache) {
      setCache(cacheKey, { coverUrl: initialUrl })
    }
  } else if (enableCache) {
    // Check cache on initialization if enabled and no initialUrl
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

  /**
   * Setup IntersectionObserver for lazy loading
   * @param {HTMLElement} element - Element to observe
   * @param {Object} options - Observer options (optional)
   */
  const setupLazyLoad = (element, options = {}) => {
    if (!element) {
      console.warn('useCover: setupLazyLoad called without element')
      return
    }

    // Don't setup observer if we already have a cover URL (from cache or initialUrl)
    if (coverUrl.value) {
      return
    }

    // Priority-based root margin for preloading
    const rootMarginMap = {
      high: '200px',   // Load early for high priority (detail views, above-fold)
      normal: '50px',  // Standard preload (default)
      low: '0px'       // Load only when in viewport (below-fold content)
    }

    const observerOptions = {
      rootMargin: rootMarginMap[priority] || rootMarginMap.normal,
      threshold: 0.1,  // Trigger when 10% of element is visible
      ...options
    }

    observer.value = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !coverUrl.value && !loading.value) {
            // Element is visible, fetch the cover
            fetchCover()
            // Stop observing once fetch initiated
            if (observer.value && observedElement.value) {
              observer.value.unobserve(observedElement.value)
            }
          }
        })
      },
      observerOptions
    )

    observedElement.value = element
    observer.value.observe(element)
  }

  /**
   * Cleanup observer on unmount
   */
  const cleanup = () => {
    if (observer.value && observedElement.value) {
      observer.value.unobserve(observedElement.value)
      observer.value.disconnect()
    }
  }

  // Auto-cleanup on unmount
  onUnmounted(cleanup)

  // Badge overlay metadata
  const badges = {
    inLibrary,
    hasAudiobook,
    seriesNumber
  }

  return {
    // Core cover state
    coverUrl,
    loading,
    error,

    // Fetch functions
    fetchCover,
    refetch,

    // Lazy loading support
    setupLazyLoad,
    cleanup,

    // Badge overlay metadata
    badges
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
