/**
 * useSeriesCache - Client-side LRU cache for series data
 *
 * Provides in-memory caching for series book data with:
 * - LRU eviction (max 50 series)
 * - 5-minute TTL matching backend cache
 * - Automatic cleanup of expired entries
 * - Methods to merge enriched data into existing cache
 */

import { ref } from 'vue'

const MAX_CACHE_SIZE = 50
const CACHE_TTL_MS = 5 * 60 * 1000  // 5 minutes (matches backend)

// Cache storage (singleton across all component instances)
const cache = ref(new Map())  // Map<string, CacheEntry>

/**
 * CacheEntry structure:
 * {
 *   seriesId: string,
 *   data: Object (series data with books array),
 *   timestamp: number (Date.now()),
 *   accessCount: number,
 *   lastAccessed: number
 * }
 */

/**
 * useSeriesCache composable
 * @returns {Object} Cache methods
 */
export function useSeriesCache() {
  /**
   * Generate cache key from series ID
   * @param {string|number} seriesId - Series identifier
   * @returns {string} Cache key
   */
  function getCacheKey(seriesId) {
    return `series_${seriesId}`
  }

  /**
   * Check if cache entry is expired
   * @param {Object} entry - Cache entry
   * @returns {boolean} True if expired
   */
  function isExpired(entry) {
    const age = Date.now() - entry.timestamp
    return age > CACHE_TTL_MS
  }

  /**
   * Clean up expired entries
   */
  function cleanup() {
    const expiredKeys = []

    for (const [key, entry] of cache.value.entries()) {
      if (isExpired(entry)) {
        expiredKeys.push(key)
      }
    }

    for (const key of expiredKeys) {
      cache.value.delete(key)
    }

    if (expiredKeys.length > 0) {
      console.log(`[useSeriesCache] Cleaned up ${expiredKeys.length} expired entries`)
    }
  }

  /**
   * Evict least recently used entry if cache is full
   */
  function evictLRU() {
    if (cache.value.size < MAX_CACHE_SIZE) {
      return
    }

    // Find least recently used entry
    let lruKey = null
    let lruTimestamp = Date.now()

    for (const [key, entry] of cache.value.entries()) {
      if (entry.lastAccessed < lruTimestamp) {
        lruKey = key
        lruTimestamp = entry.lastAccessed
      }
    }

    if (lruKey) {
      cache.value.delete(lruKey)
      console.log(`[useSeriesCache] Evicted LRU entry: ${lruKey}`)
    }
  }

  /**
   * Get series data from cache
   * @param {string|number} seriesId - Series identifier
   * @returns {Object|null} Cached series data or null if not found/expired
   */
  function get(seriesId) {
    const key = getCacheKey(seriesId)
    const entry = cache.value.get(key)

    if (!entry) {
      return null
    }

    // Check if expired
    if (isExpired(entry)) {
      cache.value.delete(key)
      return null
    }

    // Update access metadata
    entry.lastAccessed = Date.now()
    entry.accessCount++

    console.log(`[useSeriesCache] Cache hit for series ${seriesId} (${entry.accessCount} accesses)`)
    return entry.data
  }

  /**
   * Store series data in cache
   * @param {string|number} seriesId - Series identifier
   * @param {Object} data - Series data to cache
   */
  function set(seriesId, data) {
    const key = getCacheKey(seriesId)

    // Cleanup expired entries before adding new one
    cleanup()

    // Evict LRU if cache is full
    evictLRU()

    // Store new entry
    cache.value.set(key, {
      seriesId: String(seriesId),
      data: { ...data },  // Clone to avoid mutations
      timestamp: Date.now(),
      accessCount: 1,
      lastAccessed: Date.now()
    })

    console.log(`[useSeriesCache] Cached series ${seriesId} (cache size: ${cache.value.size}/${MAX_CACHE_SIZE})`)
  }

  /**
   * Merge enriched books into cached series data
   * @param {string|number} seriesId - Series identifier
   * @param {Array} enrichedBooks - Array of enriched book objects
   * @returns {boolean} True if merge succeeded, false if not in cache
   */
  function mergeBooksData(seriesId, enrichedBooks) {
    const cachedData = get(seriesId)

    if (!cachedData || !Array.isArray(cachedData.books)) {
      return false
    }

    // Merge enriched data into cached books
    cachedData.books = cachedData.books.map(existingBook => {
      const enriched = enrichedBooks.find(b =>
        (b.display_title === existingBook.display_title || b.title === existingBook.title) &&
        b.author === existingBook.author
      )

      if (enriched) {
        return {
          ...existingBook,
          ...enriched,
          enrichment_pending: false
        }
      }

      return existingBook
    })

    // Update cache with merged data
    set(seriesId, cachedData)

    console.log(`[useSeriesCache] Merged ${enrichedBooks.length} enriched books for series ${seriesId}`)
    return true
  }

  /**
   * Remove series from cache
   * @param {string|number} seriesId - Series identifier
   */
  function remove(seriesId) {
    const key = getCacheKey(seriesId)
    const deleted = cache.value.delete(key)

    if (deleted) {
      console.log(`[useSeriesCache] Removed series ${seriesId} from cache`)
    }

    return deleted
  }

  /**
   * Clear all cached data
   */
  function clear() {
    const size = cache.value.size
    cache.value.clear()
    console.log(`[useSeriesCache] Cleared all ${size} cached entries`)
  }

  /**
   * Get cache statistics
   * @returns {Object} Cache stats
   */
  function getStats() {
    const stats = {
      size: cache.value.size,
      maxSize: MAX_CACHE_SIZE,
      ttlMs: CACHE_TTL_MS,
      entries: []
    }

    for (const [key, entry] of cache.value.entries()) {
      const age = Date.now() - entry.timestamp
      stats.entries.push({
        key,
        seriesId: entry.seriesId,
        ageMs: age,
        expired: isExpired(entry),
        accessCount: entry.accessCount,
        booksCount: entry.data?.books?.length || 0
      })
    }

    return stats
  }

  return {
    get,
    set,
    mergeBooksData,
    remove,
    clear,
    getStats,
    cleanup
  }
}
