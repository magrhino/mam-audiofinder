/**
 * Discover Search Composable
 *
 * Unified search state management for the Discover view.
 * Uses a single API call (showcase) and derives both views from the same data:
 * - Cards mode: uses cardGroups (grouped by title)
 * - Table mode: uses tableResults (flattened versions from all groups)
 */

import { ref, reactive, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@composables/useApi'
import { VIEW_MODES } from '@composables/useViewToggle'

// Unified limit options - MAM only supports up to 100
export const LIMIT_OPTIONS = [
  { label: '25 results', value: '25' },
  { label: '50 results', value: '50' },
  { label: '100 results', value: '100' }
]

// Sort options (table mode only)
export const SORT_OPTIONS = [
  { label: 'Sort: Default', value: 'default' },
  { label: 'Seeders ↓', value: 'seedersDesc' },
  { label: 'Date Added ↓', value: 'dateDesc' },
  { label: 'Size ↓', value: 'sizeDesc' }
]

// Default limit
export const DEFAULT_LIMIT = '50'

/**
 * Unified search composable for Discover view
 * @param {object} options - Configuration
 * @param {import('vue').Ref<string>} options.viewMode - Reactive view mode ref
 * @returns {object} Search state and methods
 */
export function useDiscoverSearch(options = {}) {
  const { viewMode } = options

  const api = useApi()
  const route = useRoute()
  const router = useRouter()

  // Form state
  const form = reactive({
    q: '',
    limit: DEFAULT_LIMIT,
    sort: 'default'
  })

  // Search state
  const loading = ref(false)
  const status = ref('Enter a search query to get started.')

  // Results (mode-specific)
  const tableResults = ref([])      // Raw search results
  const cardGroups = ref([])        // Grouped showcase results
  const totalGroups = ref(0)
  const totalResults = ref(0)

  // Detail state (cards mode)
  const detailGroup = ref(null)

  // Computed helpers
  const hasResults = computed(() => {
    return viewMode.value === VIEW_MODES.CARDS
      ? cardGroups.value.length > 0
      : tableResults.value.length > 0
  })

  const currentLimitOptions = computed(() => LIMIT_OPTIONS)

  /**
   * Normalize query object (remove empty values)
   */
  const normalizeQuery = (values) => {
    const query = {}
    Object.entries(values).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query[key] = value
      }
    })
    return query
  }

  /**
   * Sync form state from URL query params
   */
  const syncFromRoute = () => {
    const getValue = (key, fallback) => {
      const value = route.query[key]
      if (Array.isArray(value)) {
        return value[value.length - 1] ?? fallback
      }
      return value ?? fallback
    }

    form.q = getValue('q', '')
    form.sort = getValue('sort', 'default')
    form.limit = getValue('limit', DEFAULT_LIMIT)
  }

  /**
   * Update URL with current form state
   */
  const updateUrl = () => {
    const query = normalizeQuery({
      q: form.q.trim(),
      view: viewMode.value,
      limit: form.limit,
      sort: viewMode.value === VIEW_MODES.TABLE ? form.sort : undefined,
      detail: route.query.detail // Preserve detail if exists
    })
    router.replace({ query })
  }

  /**
   * Clear all results
   */
  const clearResults = () => {
    tableResults.value = []
    cardGroups.value = []
    totalGroups.value = 0
    totalResults.value = 0
    detailGroup.value = null
  }

  /**
   * Run unified search - always uses showcase API
   * Both cardGroups and tableResults are populated from a single API call.
   * @param {object} options - Search options
   * @param {boolean} options.silent - If true, don't update status during search
   */
  const runSearch = async (options = {}) => {
    const { silent = false } = options

    if (!form.q.trim()) {
      status.value = 'Enter a search query to get started.'
      clearResults()
      return
    }

    loading.value = true
    if (!silent) {
      status.value = 'Searching...'
    }
    clearResults()

    try {
      // Always use showcase API - returns grouped data that can be flattened
      const data = await api.getShowcase({
        query: form.q.trim(),
        limit: parseInt(form.limit, 10)
      })

      // Store grouped results for cards mode
      cardGroups.value = data.groups || []
      totalGroups.value = data.total_groups || 0
      totalResults.value = data.total_results || 0

      // Derive flat results for table mode by flattening all versions
      tableResults.value = cardGroups.value.flatMap(group => group.versions || [])

      // Update status - both result sets now always populated
      status.value = cardGroups.value.length
        ? `Found ${totalGroups.value} titles (${totalResults.value} editions)`
        : 'No audiobooks found.'

      updateUrl()
    } catch (err) {
      console.error('Search failed:', err)
      status.value = `Search failed: ${err.message}`
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear search and results
   */
  const clearSearch = () => {
    form.q = ''
    clearResults()
    status.value = 'Enter a search query to get started.'
  }

  /**
   * Show detail view for a card group
   * @param {object} group - Group to show detail for
   */
  const showDetail = (group) => {
    detailGroup.value = group

    // Update URL with detail parameter
    const detailSlug = group.normalized_title ||
      group.display_title?.toLowerCase().replace(/\s+/g, '-') ||
      'unknown'

    router.push({
      query: {
        ...route.query,
        detail: detailSlug
      }
    })
  }

  /**
   * Close detail view
   */
  const closeDetail = () => {
    detailGroup.value = null

    // Remove detail parameter from URL
    const query = { ...route.query }
    delete query.detail
    router.replace({ query })
  }

  /**
   * Restore detail view from URL parameter
   */
  const restoreDetailFromUrl = () => {
    const detailId = route.query.detail
    if (!detailId || !cardGroups.value.length) return

    const group = cardGroups.value.find(g =>
      g.normalized_title === detailId ||
      g.display_title?.toLowerCase().replace(/\s+/g, '-') === detailId
    )

    if (group) {
      detailGroup.value = group
    }
  }

  /**
   * Handle view mode change
   * With unified search, both result sets are always populated.
   * No limit adjustment or re-search needed.
   */
  const handleViewModeChange = (newMode, oldMode) => {
    // No-op: limits are unified, and both result sets are already populated
    // Kept for API compatibility with DiscoverView
  }

  // NOTE: No watcher here - DiscoverView handles mode changes to avoid race conditions

  // Watch for URL query changes (browser back/forward)
  watch(() => route.query.detail, (newDetail, oldDetail) => {
    if (viewMode.value !== VIEW_MODES.CARDS) return

    if (newDetail && newDetail !== oldDetail) {
      restoreDetailFromUrl()
    } else if (!newDetail && oldDetail) {
      detailGroup.value = null
    }
  })

  return {
    // Form state
    form,

    // Search state
    loading,
    status,

    // Results
    tableResults,
    cardGroups,
    totalGroups,
    totalResults,
    hasResults,

    // Detail state (cards mode)
    detailGroup,

    // Options
    currentLimitOptions,
    SORT_OPTIONS,

    // Methods
    syncFromRoute,
    runSearch,
    clearSearch,
    clearResults,
    showDetail,
    closeDetail,
    restoreDetailFromUrl,
    handleViewModeChange
  }
}
