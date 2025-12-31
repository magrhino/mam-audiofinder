import { ref, watch } from 'vue'
import { useApi } from './useApi'

export function useLibraryBooks() {
  const api = useApi()

  const libraryId = ref(null) // null = all libraries
  const books = ref([])
  const loading = ref(false)
  const error = ref(null)
  const searchQuery = ref('')
  const seriesFilter = ref(null)
  const page = ref(1)
  const total = ref(0)
  const pages = ref(0)

  async function fetchBooks() {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams({
        page: page.value.toString(),
        limit: '50',
      })

      if (searchQuery.value) {
        params.set('q', searchQuery.value)
      }

      if (seriesFilter.value) {
        params.set('series', seriesFilter.value)
      }

      if (libraryId.value) {
        params.set('library_id', libraryId.value)
      }

      const response = await api.get(`/api/library/books?${params}`)
      books.value = response.books
      total.value = response.total
      pages.value = response.pages
    } catch (e) {
      error.value = e.message
      books.value = []
    } finally {
      loading.value = false
    }
  }

  watch([page, seriesFilter, libraryId], fetchBooks, { immediate: true })

  let timeout = null
  watch(searchQuery, () => {
    clearTimeout(timeout)
    timeout = setTimeout(() => {
      page.value = 1
      fetchBooks()
    }, 300)
  })

  return {
    libraryId,
    books,
    loading,
    error,
    searchQuery,
    seriesFilter,
    page,
    total,
    pages,
    fetchBooks,
  }
}
