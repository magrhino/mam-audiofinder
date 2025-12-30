/**
 * useHistoryLiveUpdates - Composable for live history updates
 *
 * Encapsulates:
 * - Auto-refresh with 5s interval
 * - torrentAdded event listener
 * - importCompleted event listener
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
import { useMessage } from 'naive-ui'
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
  const message = useMessage()
  const history = ref([])
  const isActive = ref(false)
  let refreshInterval = null
  let autoImportInterval = null
  let torrentAddedHandler = null
  let importCompletedHandler = null

  // Track previously seen auto-import activity IDs to avoid duplicate notifications
  const seenActivityIds = new Set()
  let isInitialLoad = true

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
   * Check auto-import status and show notifications for new completions/failures
   */
  const checkAutoImportActivity = async () => {
    try {
      const status = await api.getAutoImportStatus()
      const activities = status.recent_activity || []

      for (const activity of activities) {
        // Skip if already seen
        if (seenActivityIds.has(activity.id)) continue
        seenActivityIds.add(activity.id)

        // Skip notifications on initial load (don't notify for old items)
        if (isInitialLoad) continue

        // Show notifications based on status
        if (activity.status === 'completed') {
          message.success(`🤖 Auto-imported: "${activity.title}"`)
          // Reload history to reflect the change
          loadHistory()
        } else if (activity.status === 'failed') {
          message.error(`❌ Auto-import failed: "${activity.title}" - ${activity.reason || 'Unknown error'}`)
        }
      }

      // After first check, clear initial load flag
      isInitialLoad = false
    } catch (err) {
      console.error('[useHistoryLiveUpdates] Failed to check auto-import status:', err)
    }
  }

  /**
   * Handle import completion event
   * Updates the matching history item's status immediately, then reloads to get fresh server data
   *
   * @param {CustomEvent} event - Import completed event with detail.historyId
   */
  const handleImportCompleted = (event) => {
    const historyId = event.detail?.historyId

    if (!historyId) {
      console.warn('[useHistoryLiveUpdates] importCompleted event missing historyId')
      return
    }

    console.log(`[useHistoryLiveUpdates] importCompleted event for history ID: ${historyId}`)

    // Find and update the matching item immediately for instant UI feedback
    const item = history.value.find(h => h.id === historyId)

    if (item) {
      console.log(`[useHistoryLiveUpdates] Updating status for "${item.title}" to imported`)

      // Update status to show imported state
      item.qb_status = 'imported'
      item.qb_status_color = 'green'
      item.imported_at = new Date().toISOString().replace('T', ' ').substring(0, 19)

      // Show verification status if available from event
      if (event.detail?.verification) {
        const verification = event.detail.verification
        item.abs_verify_status = verification.status
        item.abs_verify_note = verification.note
        console.log(`[useHistoryLiveUpdates] Updated verification: ${verification.status}`)
      }
    } else {
      console.warn(`[useHistoryLiveUpdates] Could not find history item with id ${historyId}`)
    }

    // Reload full history from server to get authoritative state
    // This ensures we have the latest verification status, cover URLs, etc.
    setTimeout(() => {
      console.log('[useHistoryLiveUpdates] Reloading history after import completion')
      loadHistory()
    }, 1000)
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

    // Set up importCompleted event listener
    importCompletedHandler = handleImportCompleted
    window.addEventListener('importCompleted', importCompletedHandler)

    // Initial check for auto-import activity (populates seenActivityIds)
    checkAutoImportActivity()

    // Set up auto-import status polling (every 10s)
    autoImportInterval = setInterval(() => {
      if (isActive.value) {
        checkAutoImportActivity()
      }
    }, 10000)

    console.log('[useHistoryLiveUpdates] Auto-refresh started (interval:', interval, 'ms)')
  }

  /**
   * Stop auto-refresh interval and cleanup
   */
  const stop = () => {
    console.log('[useHistoryLiveUpdates] Stopping auto-refresh...')
    isActive.value = false

    // Clear history refresh interval
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
      console.log('[useHistoryLiveUpdates] Interval cleared')
    }

    // Clear auto-import status polling interval
    if (autoImportInterval) {
      clearInterval(autoImportInterval)
      autoImportInterval = null
      console.log('[useHistoryLiveUpdates] Auto-import interval cleared')
    }

    // Remove torrentAdded event listener
    if (torrentAddedHandler) {
      window.removeEventListener('torrentAdded', torrentAddedHandler)
      torrentAddedHandler = null
      console.log('[useHistoryLiveUpdates] torrentAdded listener removed')
    }

    // Remove importCompleted event listener
    if (importCompletedHandler) {
      window.removeEventListener('importCompleted', importCompletedHandler)
      importCompletedHandler = null
      console.log('[useHistoryLiveUpdates] importCompleted listener removed')
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
