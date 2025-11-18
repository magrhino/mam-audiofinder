/**
 * useHistoryLiveUpdates - Composable for live history updates
 *
 * Encapsulates:
 * - Auto-refresh with 5s interval
 * - torrentAdded event listener
 * - Lifecycle management (cleanup on unmount)
 * - start/stop controls for router integration
 *
 * @example
 * // Basic usage (auto-starts on mount, auto-stops on unmount)
 * const { history, loadHistory } = useHistoryLiveUpdates({ interval: 5000 })
 *
 * @example
 * // Advanced: Router integration (pause on navigation)
 * const { history, loadHistory, start, stop } = useHistoryLiveUpdates({ interval: 5000 })
 * watch(() => route.name, (newRoute) => {
 *   if (newRoute === 'history') {
 *     start()
 *   } else {
 *     stop()
 *   }
 * })
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useApi } from './useApi'

/**
 * Composable for managing live history updates
 *
 * @param {Object} options - Configuration options
 * @param {number} options.interval - Refresh interval in milliseconds (default: 5000)
 * @returns {Object} - { history, loadHistory, start, stop, isActive }
 */
export function useHistoryLiveUpdates(options = {}) {
  const { interval = 5000 } = options

  const api = useApi()
  const history = ref([])
  const isActive = ref(false)
  let refreshInterval = null
  let torrentAddedHandler = null

  /**
   * Load history data from API
   */
  const loadHistory = async () => {
    try {
      console.log('[useHistoryLiveUpdates] Loading history...')
      const data = await api.getHistory()
      history.value = data.items || []
      console.log(`[useHistoryLiveUpdates] Loaded ${history.value.length} items`)
    } catch (err) {
      console.error('[useHistoryLiveUpdates] Failed to load history:', err)
    }
  }

  /**
   * Start auto-refresh interval
   */
  const start = () => {
    if (isActive.value) {
      console.log('[useHistoryLiveUpdates] Already active, skipping start')
      return
    }

    console.log('[useHistoryLiveUpdates] Starting auto-refresh...')
    isActive.value = true

    // Initial load
    loadHistory()

    // Set up interval for auto-refresh
    refreshInterval = setInterval(() => {
      if (isActive.value) {
        console.log('[useHistoryLiveUpdates] Auto-refresh tick')
        loadHistory()
      }
    }, interval)

    // Set up torrentAdded event listener
    torrentAddedHandler = () => {
      console.log('[useHistoryLiveUpdates] torrentAdded event received')
      loadHistory()
    }
    window.addEventListener('torrentAdded', torrentAddedHandler)

    console.log('[useHistoryLiveUpdates] Auto-refresh started (interval:', interval, 'ms)')
  }

  /**
   * Stop auto-refresh interval and cleanup
   */
  const stop = () => {
    console.log('[useHistoryLiveUpdates] Stopping auto-refresh...')
    isActive.value = false

    // Clear interval
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
      console.log('[useHistoryLiveUpdates] Interval cleared')
    }

    // Remove event listener
    if (torrentAddedHandler) {
      window.removeEventListener('torrentAdded', torrentAddedHandler)
      torrentAddedHandler = null
      console.log('[useHistoryLiveUpdates] Event listener removed')
    }
  }

  // Lifecycle hooks
  onMounted(() => {
    console.log('[useHistoryLiveUpdates] Component mounted')
    start()
  })

  onUnmounted(() => {
    console.log('[useHistoryLiveUpdates] Component unmounting')
    stop()
  })

  // Return reactive state and controls
  return {
    history,
    loadHistory,
    start,
    stop,
    isActive
  }
}
