import { ref, watch } from 'vue'
import { useApi } from './useApi'

export function useLibrarySeries() {
  const api = useApi()

  const source = ref('abs')
  const series = ref([])
  const loading = ref(false)
  const error = ref(null)
  const searchQuery = ref('')
  const page = ref(1)
  const total = ref(0)
  const pages = ref(0)

  async function fetchSeries() {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams({
        source: source.value,
        page: page.value.toString(),
        limit: '50',
      })

      if (searchQuery.value) {
        params.set('q', searchQuery.value)
      }

      const response = await api.get(`/api/library/series?${params}`)
      series.value = response.series
      total.value = response.total
      pages.value = response.pages
    } catch (e) {
      error.value = e.message
      series.value = []
    } finally {
      loading.value = false
    }
  }

  // Refetch on source/page change
  watch([source, page], fetchSeries, { immediate: true })

  // Debounced search
  let timeout = null
  watch(searchQuery, () => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      page.value = 1
      fetchSeries()
    }, 300)
  })

  return {
    source,
    series,
    loading,
    error,
    searchQuery,
    page,
    total,
    pages,
    fetchSeries,
  }
}
