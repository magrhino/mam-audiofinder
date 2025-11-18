/**
 * useCover Composable
 * Simple composable for fetching cover URLs from the backend
 * Used with NaiveUI's n-image component which handles lazy loading
 */

import { ref } from 'vue'
import { useApi } from '../useApi.js'

/**
 * Create a cover fetcher for a specific item
 * @param {Object} params - Cover parameters
 * @param {string} params.mamId - MAM torrent ID
 * @param {string} params.title - Book title
 * @param {string} params.author - Author name
 * @returns {Object} Cover state and fetch function
 */
export function useCover({ mamId, title, author }) {
  const api = useApi()
  const coverUrl = ref('')
  const loading = ref(false)
  const error = ref('')

  /**
   * Fetch cover from backend
   */
  const fetchCover = async () => {
    if (!mamId || !title) {
      error.value = 'Missing required info'
      return
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

  return {
    coverUrl,
    loading,
    error,
    fetchCover
  }
}

/**
 * Create a shared cover cache for efficient loading
 * Maps mamId to cover URL to avoid redundant API calls
 */
const coverCache = new Map()

/**
 * Get or fetch a cover URL with caching
 * @param {string} mamId - MAM torrent ID
 * @param {string} title - Book title
 * @param {string} author - Author name
 * @returns {Promise<string>} Cover URL or empty string
 */
export async function getCoverUrl(mamId, title, author) {
  // Check cache first
  if (coverCache.has(mamId)) {
    return coverCache.get(mamId)
  }

  // Fetch from API
  const { coverUrl, fetchCover } = useCover({ mamId, title, author })
  await fetchCover()

  // Cache the result
  if (coverUrl.value) {
    coverCache.set(mamId, coverUrl.value)
  }

  return coverUrl.value
}
