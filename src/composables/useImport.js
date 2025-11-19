/**
 * useImport composable - Import workflow logic
 * Handles torrent import with validation, multi-disc detection, and status messaging
 */

import { ref, reactive, computed, watch } from 'vue'
import { useApi } from './useApi'

/**
 * Composable for import workflow (torrents to library)
 * @param {Object} historyItem - History item to import
 * @returns {Object} Import state and methods
 */
export function useImport(historyItem) {
  const api = useApi()

  const loading = ref(false)
  const torrents = ref([])
  const torrentTree = ref(null)
  const statusMessage = ref('')
  const buttonLabel = ref('Copy to Library')
  const formLoaded = ref(false)
  const showTree = ref(false)

  const form = reactive({
    author: historyItem?.author || '',
    title: historyItem?.title || '',
    selectedHash: historyItem?.qb_hash || '',
    flatten: false
  })

  /**
   * Load configuration and torrents
   */
  const loadFormData = async () => {
    if (formLoaded.value) return

    formLoaded.value = true
    loading.value = true
    statusMessage.value = ''

    try {
      // Fetch import mode configuration
      const cfg = await api.getConfig()
      if (cfg.import_mode === 'link') {
        buttonLabel.value = 'Link to Library'
      } else if (cfg.import_mode === 'move') {
        buttonLabel.value = 'Move to Library'
      }
    } catch (err) {
      console.warn('Failed to fetch config', err)
    }

    try {
      // Fetch completed torrents
      const data = await api.getCompletedTorrents()
      torrents.value = data.items || []

      // Auto-select matching torrent
      if (!form.selectedHash && historyItem) {
        const match = torrents.value.find(t =>
          t.hash === historyItem.qb_hash ||
          String(t.mam_id || '') === String(historyItem.mam_id || '')
        )

        if (match) {
          form.selectedHash = match.hash
          statusMessage.value = '✓ Auto-selected matching torrent'
        }
      }
    } catch (err) {
      console.error('Failed to load torrents', err)
      statusMessage.value = 'Failed to load torrents'
    } finally {
      loading.value = false
    }
  }

  /**
   * Load torrent file tree for preview and multi-disc detection
   */
  const loadTorrentTree = async (hash) => {
    if (!hash) {
      torrentTree.value = null
      showTree.value = false
      return
    }

    loading.value = true
    try {
      const data = await api.getTorrentTree(hash)
      torrentTree.value = data

      // Auto-enable flatten if multi-disc detected
      if (data?.has_multi_disc && !form.flatten) {
        form.flatten = true
        statusMessage.value = '💿 Multi-disc structure detected - flatten enabled'
      }
    } catch (err) {
      console.error('Failed to load torrent tree', err)
      statusMessage.value = 'Failed to load file tree'
      torrentTree.value = null
      showTree.value = false
    } finally {
      loading.value = false
    }
  }

  /**
   * Perform the import with validation
   */
  const performImport = async () => {
    // Validate torrent selection
    if (!form.selectedHash) {
      statusMessage.value = '⚠️ Select a torrent to import'
      return { success: false, message: 'No torrent selected' }
    }

    // Validate author and title
    if (!form.author?.trim() || !form.title?.trim()) {
      statusMessage.value = '⚠️ Author and title are required'
      return { success: false, message: 'Missing required fields' }
    }

    loading.value = true
    statusMessage.value = 'Importing…'

    try {
      const result = await api.importTorrent({
        author: form.author.trim(),
        title: form.title.trim(),
        hash: form.selectedHash,
        history_id: historyItem?.id,
        flatten: form.flatten
      })

      statusMessage.value = '✓ Import requested'

      // Dispatch event for live status updates
      if (historyItem?.id) {
        window.dispatchEvent(new CustomEvent('importCompleted', {
          detail: {
            historyId: historyItem.id,
            verification: result.verification
          }
        }))
      }

      return { success: true, result }
    } catch (err) {
      const message = `Import failed: ${err.message}`
      statusMessage.value = `❌ ${message}`
      return { success: false, message, error: err }
    } finally {
      loading.value = false
    }
  }

  /**
   * Toggle tree view visibility
   */
  const toggleTree = () => {
    showTree.value = !showTree.value
    if (showTree.value && !torrentTree.value) {
      loadTorrentTree(form.selectedHash)
    }
  }

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    form.author = historyItem?.author || ''
    form.title = historyItem?.title || ''
    form.selectedHash = historyItem?.qb_hash || ''
    form.flatten = false
    statusMessage.value = ''
    torrentTree.value = null
    showTree.value = false
  }

  // Computed properties
  const selectedTorrent = computed(() => {
    return torrents.value.find(t => t.hash === form.selectedHash)
  })

  const hasMultiDisc = computed(() => {
    return torrentTree.value?.has_multi_disc || false
  })

  const canImport = computed(() => {
    return !loading.value &&
           form.selectedHash &&
           form.author?.trim() &&
           form.title?.trim()
  })

  const treeContents = computed(() => {
    if (!torrentTree.value?.files) return []
    return torrentTree.value.files
  })

  const toggleTreeLabel = computed(() => {
    return showTree.value ? 'Hide Files' : '📁 View Files'
  })

  // Check for torrent mismatch (selected torrent doesn't match history item)
  const torrentMismatchWarning = computed(() => {
    if (!historyItem || !form.selectedHash) return null

    const selected = selectedTorrent.value
    if (!selected) return null

    const historyMamId = String(historyItem.mam_id || '').trim()
    const selectedMamId = String(selected.mam_id || '').trim()
    const historyHash = historyItem.qb_hash

    // If matched by hash, no mismatch
    if (historyHash && form.selectedHash === historyHash) {
      return null
    }

    // If both have mam_id and they match, no mismatch
    if (historyMamId && selectedMamId && historyMamId === selectedMamId) {
      return null
    }

    // If neither has mam_id, we can't determine mismatch reliably
    if (!historyMamId && !selectedMamId) {
      return null
    }

    // Otherwise, it's a potential mismatch
    const selectedName = selected.name || 'Unknown'
    const expectedName = historyItem.title || 'Unknown'

    return {
      warning: '⚠️ This torrent does not match the history item',
      detail: `Selected: ${selectedName} | Expected: ${expectedName}`
    }
  })

  // Contextual messaging
  const contextualMessage = computed(() => {
    // Check for torrent mismatch first (highest priority warning)
    if (torrentMismatchWarning.value) {
      return `${torrentMismatchWarning.value.warning}\n${torrentMismatchWarning.value.detail}`
    }

    if (!form.author?.trim() || !form.title?.trim()) {
      return '⚠️ Author and title are required for import'
    }

    if (hasMultiDisc.value && !form.flatten) {
      return '💿 Multi-disc structure detected - consider enabling flatten'
    }

    if (hasMultiDisc.value && form.flatten) {
      return '✓ Multi-disc will be flattened to sequential files'
    }

    if (!form.selectedHash) {
      return 'Select a torrent to import'
    }

    return ''
  })

  // Watch for torrent selection changes to auto-fetch tree
  watch(() => form.selectedHash, (newHash) => {
    if (newHash) {
      loadTorrentTree(newHash)
    } else {
      torrentTree.value = null
      showTree.value = false
    }
  })

  return {
    // State
    loading,
    torrents,
    torrentTree,
    statusMessage,
    buttonLabel,
    formLoaded,
    showTree,
    form,

    // Computed
    selectedTorrent,
    hasMultiDisc,
    canImport,
    treeContents,
    toggleTreeLabel,
    contextualMessage,

    // Methods
    loadFormData,
    loadTorrentTree,
    performImport,
    toggleTree,
    resetForm
  }
}

/**
 * Composable for verifying imported items in Audiobookshelf
 * @returns {Object} Verification state and methods
 */
export function useVerification() {
  const api = useApi()
  const verifying = ref(false)
  const verificationResult = ref(null)

  /**
   * Verify a history item against Audiobookshelf library
   * @param {number} historyId - History item ID
   */
  const verifyItem = async (historyId) => {
    verifying.value = true
    verificationResult.value = null

    try {
      const result = await api.verifyHistoryItem(historyId)
      verificationResult.value = result
      return { success: true, result }
    } catch (err) {
      const error = `Verification failed: ${err.message}`
      verificationResult.value = { error }
      return { success: false, error: err }
    } finally {
      verifying.value = false
    }
  }

  /**
   * Clear verification result
   */
  const clearResult = () => {
    verificationResult.value = null
  }

  return {
    verifying,
    verificationResult,
    verifyItem,
    clearResult
  }
}
