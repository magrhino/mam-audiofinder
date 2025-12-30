/**
 * View Toggle Composable
 *
 * Manages the view mode state (cards/table) for the Discover view.
 * - Persists preference to localStorage
 * - Syncs with URL query parameter
 * - Provides reactive view state
 */

import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'

// View mode constants
export const VIEW_MODES = {
  CARDS: 'cards',
  TABLE: 'table'
}

/**
 * Get reactive view toggle state
 * @param {object} options - Configuration options
 * @param {string} options.defaultMode - Default view mode ('cards' or 'table')
 * @returns {object} View toggle state and methods
 */
export function useViewToggle(options = {}) {
  const { defaultMode = VIEW_MODES.CARDS } = options

  const route = useRoute()
  const router = useRouter()

  // Persistent storage for user preference
  const storedPreference = useLocalStorage('discover-view-mode', defaultMode)

  // Current view mode (reactive)
  const viewMode = ref(defaultMode)

  // Computed helpers
  const isCardsMode = computed(() => viewMode.value === VIEW_MODES.CARDS)
  const isTableMode = computed(() => viewMode.value === VIEW_MODES.TABLE)

  /**
   * Initialize view mode from URL or localStorage
   */
  const initFromRoute = () => {
    const urlView = route.query.view
    if (urlView === VIEW_MODES.CARDS || urlView === VIEW_MODES.TABLE) {
      viewMode.value = urlView
    } else {
      // Use stored preference if no URL param
      viewMode.value = storedPreference.value
    }
  }

  /**
   * Set view mode and update URL
   * @param {string} mode - 'cards' or 'table'
   */
  const setViewMode = (mode) => {
    if (mode !== VIEW_MODES.CARDS && mode !== VIEW_MODES.TABLE) {
      console.warn(`Invalid view mode: ${mode}`)
      return
    }

    viewMode.value = mode
    storedPreference.value = mode

    // Update URL without triggering navigation
    const query = { ...route.query, view: mode }
    router.replace({ query })
  }

  /**
   * Toggle between cards and table modes
   */
  const toggleViewMode = () => {
    setViewMode(isCardsMode.value ? VIEW_MODES.TABLE : VIEW_MODES.CARDS)
  }

  // Watch for URL changes (e.g., browser back/forward)
  watch(
    () => route.query.view,
    (newView) => {
      if (newView === VIEW_MODES.CARDS || newView === VIEW_MODES.TABLE) {
        viewMode.value = newView
      }
    }
  )

  return {
    // State
    viewMode,
    isCardsMode,
    isTableMode,

    // Methods
    initFromRoute,
    setViewMode,
    toggleViewMode,

    // Constants
    VIEW_MODES
  }
}
