/**
 * useDetailView Composable
 * Reusable detail view logic with cover/description fetching, URL state management, and scroll behavior
 * Used by ShowcaseView and SeriesView for consistent detail panel implementation
 */

import { ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '../useApi.js'

/**
 * Create a detail view manager with cover/description fetching and URL state
 * @param {Object} config - Configuration object
 * @param {Function} config.normalizeDetailId - Function to convert item to URL-friendly ID
 * @param {Function} config.findItemById - Function to find item from list by detail ID
 * @param {Array} config.items - Reactive reference to items list
 * @returns {Object} Detail view state and methods
 */
export function useDetailView(config = {}) {
  const {
    normalizeDetailId = (item) => item.normalized_title || item.display_title?.toLowerCase().replace(/\s+/g, '-') || 'unknown',
    findItemById = (items, detailId) => items.find(item =>
      normalizeDetailId(item) === detailId
    ),
    items = ref([])
  } = config

  const api = useApi()
  const router = useRouter()
  const route = useRoute()

  // Detail view state
  const detailItem = ref(null)
  const detailElement = ref(null)
  const detailCoverUrl = ref('')
  const detailDescription = ref('')
  const descriptionLoading = ref(false)
  const descriptionCollapsed = ref(true)

  /**
   * Show detail view for an item
   * @param {Object} item - Item to display details for
   * @param {Object} options - Options
   * @param {boolean} options.updateUrl - Whether to update URL (default: true)
   * @param {boolean} options.scrollToView - Whether to scroll to detail (default: true)
   * @param {boolean} options.fetchCover - Whether to fetch cover (default: true)
   */
  const showDetail = async (item, options = {}) => {
    const {
      updateUrl = true,
      scrollToView = true,
      fetchCover = true
    } = options

    console.log('showDetail called with:', item)

    detailItem.value = item
    detailCoverUrl.value = ''
    detailDescription.value = ''
    descriptionCollapsed.value = true

    // Update URL with detail parameter
    if (updateUrl) {
      router.push({
        query: {
          ...route.query,
          detail: normalizeDetailId(item)
        }
      })
    }

    // Scroll to detail view after DOM updates
    if (scrollToView) {
      await nextTick()
      if (detailElement.value?.$el) {
        detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }

    // Load cover and description separately for lazy loading effect
    if (fetchCover && item.mam_id && item.display_title) {
      descriptionLoading.value = true

      try {
        const data = await api.fetchCover({
          mam_id: item.mam_id,
          title: item.display_title,
          author: item.author || '',
          max_retries: '3'
        })

        // Set cover URL
        detailCoverUrl.value = data.cover_url || ''

        // Set description if available
        if (data.description) {
          detailDescription.value = data.description
        }
      } catch (err) {
        console.warn('Failed to load detail cover and description:', err)
      } finally {
        descriptionLoading.value = false
      }
    }
  }

  /**
   * Close detail view and clear state
   */
  const closeDetail = () => {
    detailItem.value = null
    detailCoverUrl.value = ''
    detailDescription.value = ''
    descriptionLoading.value = false

    // Remove detail parameter from URL
    const query = { ...route.query }
    delete query.detail
    router.replace({ query })
  }

  /**
   * Restore detail view from URL parameter
   * Useful for browser back/forward navigation or page refresh
   */
  const restoreDetailFromUrl = async () => {
    const detailId = route.query.detail
    if (!detailId || !items.value.length) return

    // Find matching item by normalized ID
    const item = findItemById(items.value, detailId)

    if (item) {
      // Show detail without updating URL (already in URL)
      await showDetail(item, {
        updateUrl: false,
        scrollToView: true,
        fetchCover: true
      })
    }
  }

  /**
   * Toggle description collapsed state
   */
  const toggleDescription = () => {
    descriptionCollapsed.value = !descriptionCollapsed.value
  }

  return {
    // State
    detailItem,
    detailElement,
    detailCoverUrl,
    detailDescription,
    descriptionLoading,
    descriptionCollapsed,

    // Methods
    showDetail,
    closeDetail,
    restoreDetailFromUrl,
    toggleDescription
  }
}
