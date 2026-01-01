import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

/**
 * Composable for managing Hardcover series links.
 */
export function useHardcoverLink() {
  const api = useApi()

  const loading = ref(false)
  const error = ref(null)
  const searchResults = ref([])
  const currentLink = ref(null)

  /**
   * Search for Hardcover series by title.
   * @param {string} title - Series title to search for
   * @param {number} limit - Maximum results (default: 10)
   */
  async function searchSeries(title, limit = 10) {
    if (!title || title.trim().length < 2) {
      searchResults.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await api.post('/api/series/search', {
        title: title.trim(),
        limit,
      })

      if (response.hardcover_series) {
        searchResults.value = response.hardcover_series
      } else {
        searchResults.value = []
        error.value = response.error || 'No series found'
      }
    } catch (e) {
      console.error('Failed to search Hardcover series:', e)
      error.value = 'Search failed'
      searchResults.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Get the current link for a series.
   * @param {string} seriesName - Series name to lookup
   * @param {string} libraryId - Optional library ID
   */
  async function getLink(seriesName, libraryId = null) {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (libraryId) params.set('library_id', libraryId)

      const url = `/api/library/series/${encodeURIComponent(seriesName)}/link${params.toString() ? '?' + params : ''}`
      const response = await api.get(url)

      if (response.ok !== false) {
        currentLink.value = response
        return response
      } else {
        currentLink.value = null
        return null
      }
    } catch (e) {
      console.error('Failed to get series link:', e)
      currentLink.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Link a series to a Hardcover series.
   * @param {string} seriesName - Local series name
   * @param {object} hardcoverSeries - Hardcover series data
   * @param {string} libraryId - Optional library ID
   * @param {boolean} isManual - Whether this is a manual override
   */
  async function linkSeries(seriesName, hardcoverSeries, libraryId = null, isManual = true) {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (libraryId) params.set('library_id', libraryId)

      const url = `/api/library/series/${encodeURIComponent(seriesName)}/link${params.toString() ? '?' + params : ''}`

      const response = await api.post(url, {
        hardcover_series_id: hardcoverSeries.series_id,
        hardcover_series_name: hardcoverSeries.series_name,
        hardcover_author_name: hardcoverSeries.author_name,
        hardcover_book_count: hardcoverSeries.book_count,
        confidence: isManual ? 1.0 : 0.8,
      })

      if (response.ok !== false && response.success) {
        currentLink.value = {
          linked: true,
          hardcover_series_id: hardcoverSeries.series_id,
          hardcover_series_name: hardcoverSeries.series_name,
          link_confidence: isManual ? 1.0 : 0.8,
          linked_by: isManual ? 'manual' : 'auto',
        }
        return { success: true }
      } else {
        error.value = response.error || 'Failed to link series'
        return { success: false, error: error.value }
      }
    } catch (e) {
      console.error('Failed to link series:', e)
      error.value = 'Link failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  /**
   * Remove the link for a series.
   * @param {string} seriesName - Series name to unlink
   * @param {string} libraryId - Optional library ID
   */
  async function unlinkSeries(seriesName, libraryId = null) {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (libraryId) params.set('library_id', libraryId)

      const url = `/api/library/series/${encodeURIComponent(seriesName)}/link${params.toString() ? '?' + params : ''}`
      const response = await api.delete(url)

      if (response.ok !== false && response.success) {
        currentLink.value = { linked: false }
        return { success: true }
      } else {
        error.value = response.error || 'Failed to unlink series'
        return { success: false, error: error.value }
      }
    } catch (e) {
      console.error('Failed to unlink series:', e)
      error.value = 'Unlink failed'
      return { success: false, error: error.value }
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear search results and error state.
   */
  function reset() {
    searchResults.value = []
    error.value = null
    currentLink.value = null
  }

  return {
    loading,
    error,
    searchResults,
    currentLink,
    searchSeries,
    getLink,
    linkSeries,
    unlinkSeries,
    reset,
  }
}
