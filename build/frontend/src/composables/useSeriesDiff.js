import { ref } from 'vue'
import { useApi } from './useApi'

export function useSeriesDiff() {
  const api = useApi()

  const diffResult = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const selectedMissing = ref(new Set())

  async function fetchDiff(seriesName, hardcoverSeriesId = null) {
    loading.value = true
    error.value = null
    selectedMissing.value = new Set()

    try {
      const params = new URLSearchParams()
      if (hardcoverSeriesId) {
        params.set('hardcover_series_id', hardcoverSeriesId.toString())
      }

      const url = `/api/library/series/${encodeURIComponent(seriesName)}/diff?${params}`
      diffResult.value = await api.get(url)
    } catch (e) {
      error.value = e.message
      diffResult.value = null
    } finally {
      loading.value = false
    }
  }

  function toggleSelection(bookId) {
    if (selectedMissing.value.has(bookId)) {
      selectedMissing.value.delete(bookId)
    } else {
      selectedMissing.value.add(bookId)
    }
    // Trigger reactivity
    selectedMissing.value = new Set(selectedMissing.value)
  }

  function selectAll() {
    if (diffResult.value?.missing) {
      selectedMissing.value = new Set(
        diffResult.value.missing.map(m => m.hardcover?.book_id)
      )
    }
  }

  function clearSelection() {
    selectedMissing.value = new Set()
  }

  async function addSelectedToWishlist() {
    if (!diffResult.value?.missing) return []

    const results = []

    for (const item of diffResult.value.missing) {
      const hc = item.hardcover
      if (!selectedMissing.value.has(hc?.book_id)) continue

      try {
        const result = await api.post('/api/library/wishlist', {
          hardcover_book_id: hc.book_id,
          title: hc.title,
          author: hc.authors?.[0] || hc.author_names?.[0],
          series_name: diffResult.value.series_name,
          series_index: hc.position,
          cover_url: hc.cover_url || hc.image?.url,
        })
        results.push({ success: true, ...result })
      } catch (e) {
        results.push({ success: false, error: e.message, title: hc.title })
      }
    }

    return results
  }

  return {
    diffResult,
    loading,
    error,
    selectedMissing,
    fetchDiff,
    toggleSelection,
    selectAll,
    clearSelection,
    addSelectedToWishlist,
  }
}
