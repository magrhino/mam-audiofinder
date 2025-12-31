/**
 * useAddTorrentFlow Composable
 * Unified add torrent workflow with loading state, confirmation dialog, and navigation
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDialog, useMessage } from 'naive-ui'
import { useApi } from './useApi'

export function useAddTorrentFlow() {
  const api = useApi()
  const router = useRouter()
  const dialog = useDialog()
  const message = useMessage()

  const loading = ref(false)
  const loadingItems = ref(new Set()) // Track individual items being added

  /**
   * Add a torrent and optionally show confirmation dialog
   * @param {object} rowState - Row data containing torrent details
   * @param {boolean} showConfirmation - Whether to show success dialog (default: true)
   * @returns {Promise<{success: boolean, message: string}>}
   */
  const addTorrent = async (rowState, showConfirmation = true) => {
    const itemId = String(rowState.id ?? '')

    // Mark this specific item as loading
    loadingItems.value.add(itemId)
    loading.value = true

    try {
      await api.addTorrent({
        id: itemId,
        title: rowState.title || '',
        dl: rowState.dl || '',
        author: rowState.author_info || '',
        narrator: rowState.narrator_info || '',
        abs_cover_url: rowState.abs_cover_url || '',
        abs_item_id: rowState.abs_item_id || ''
      })

      // Dispatch event for live updates
      window.dispatchEvent(new CustomEvent('torrentAdded'))

      // Show toast notification
      message.success(`✓ "${rowState.title}" added to qBittorrent`)

      const successMessage = `✓ Added "${rowState.title}" to qBittorrent`

      // Show confirmation dialog if requested
      if (showConfirmation) {
        dialog.success({
          title: 'Torrent Added',
          content: `"${rowState.title}" has been added to qBittorrent successfully.`,
          positiveText: '→ Go to History',
          negativeText: 'Continue Browsing',
          onPositiveClick: () => {
            router.push('/history')
          }
        })
      }

      return { success: true, message: successMessage }
    } catch (err) {
      const errorMessage = `Add failed: ${err.message}`

      // Show toast notification
      message.error(`Failed to add "${rowState.title}"`)

      // Show error dialog
      dialog.error({
        title: 'Add Failed',
        content: errorMessage,
        positiveText: 'OK'
      })

      return { success: false, message: errorMessage }
    } finally {
      loadingItems.value.delete(itemId)
      loading.value = loadingItems.value.size > 0
    }
  }

  /**
   * Check if a specific item is currently loading
   * @param {string|number} itemId - The item ID to check
   * @returns {boolean}
   */
  const isItemLoading = (itemId) => {
    return loadingItems.value.has(String(itemId))
  }

  return {
    loading,
    addTorrent,
    isItemLoading
  }
}
