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
  const statusMessage = ref('') // Transient action feedback (importing, loading, etc.)
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

      // Auto-select matching torrent (don't set status message - let contextual message handle it)
      if (!form.selectedHash && historyItem) {
        const match = torrents.value.find(t =>
          t.hash === historyItem.qb_hash ||
          String(t.mam_id || '') === String(historyItem.mam_id || '')
        )

        if (match) {
          form.selectedHash = match.hash
          // Don't set statusMessage here - validation warnings go in contextualMessage
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
      }
      // Auto-disable flatten if no multi-disc detected
      else if (!data?.has_multi_disc && form.flatten) {
        form.flatten = false
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

      // Build detailed status message based on import results
      const { files_copied = 0, files_linked = 0, files_moved = 0, import_mode = 'link' } = result
      let statusParts = []

      if (import_mode === 'link') {
        if (files_linked > 0) {
          statusParts.push(`✓ Hard linked ${files_linked} file${files_linked !== 1 ? 's' : ''} successfully`)
        }
        const failed_links = files_copied - files_linked
        if (failed_links > 0) {
          statusParts.push(`⚠️ Copied ${failed_links} file${failed_links !== 1 ? 's' : ''} (hardlink failed)`)
        }
      } else if (import_mode === 'copy') {
        statusParts.push(`✓ Copied ${files_copied} file${files_copied !== 1 ? 's' : ''} successfully`)
      } else if (import_mode === 'move') {
        statusParts.push(`✓ Moved ${files_moved} file${files_moved !== 1 ? 's' : ''} successfully`)
      }

      // Add destination path
      if (result.dest) {
        statusParts.push(`📁 ${result.dest}`)
      }

      statusMessage.value = statusParts.join('\n')

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

    // Positive match criteria (no warning if these match)
    // 1. Hash match (most reliable)
    if (historyHash && form.selectedHash === historyHash) {
      return null
    }

    // 2. MAM ID match (reliable if both present)
    if (historyMamId && selectedMamId && historyMamId === selectedMamId) {
      return null
    }

    // If we reach here, we don't have a positive match
    // Show warning if we have evidence of mismatch

    // 3. Hash mismatch (different known hashes)
    if (historyHash && historyHash !== form.selectedHash) {
      const selectedName = selected.name || 'Unknown'
      const expectedName = historyItem.title || 'Unknown'
      return {
        warning: '⚠️ This torrent does not match the history item',
        detail: `Selected: ${selectedName} | Expected: ${expectedName}`
      }
    }

    // 4. MAM ID mismatch (different known IDs)
    if (historyMamId && selectedMamId && historyMamId !== selectedMamId) {
      const selectedName = selected.name || 'Unknown'
      const expectedName = historyItem.title || 'Unknown'
      return {
        warning: '⚠️ This torrent does not match the history item',
        detail: `Selected: ${selectedName} | Expected: ${expectedName}`
      }
    }

    // 5. One has MAM ID, other doesn't (likely mismatch unless it's the auto-selected one)
    if ((historyMamId && !selectedMamId) || (!historyMamId && selectedMamId)) {
      // If this was auto-selected and we don't have both IDs to compare, trust the auto-selection
      // Otherwise show warning
      if (!historyHash) {
        // No hash to verify against, and MAM IDs don't both exist
        const selectedName = selected.name || 'Unknown'
        const expectedName = historyItem.title || 'Unknown'
        return {
          warning: '⚠️ This torrent does not match the history item',
          detail: `Selected: ${selectedName} | Expected: ${expectedName}`
        }
      }
    }

    // If we can't determine either way, don't show warning
    // (e.g., neither has hash or MAM ID to compare)
    return null
  })

  // Contextual messaging - can show multiple warnings/messages
  const contextualMessage = computed(() => {
    const messages = []

    // Priority 1: Torrent mismatch warning (critical)
    if (torrentMismatchWarning.value) {
      messages.push(torrentMismatchWarning.value.warning)
      messages.push(torrentMismatchWarning.value.detail)
    }

    // Priority 2: Missing required fields
    if (!form.author?.trim() || !form.title?.trim()) {
      messages.push('⚠️ Author and title are required for import')
    }

    // Priority 3: Multi-disc detection (can appear alongside mismatch warning)
    if (hasMultiDisc.value && !form.flatten) {
      messages.push('💿 Multi-disc structure detected - consider enabling flatten')
    } else if (hasMultiDisc.value && form.flatten) {
      messages.push('✓ Multi-disc will be flattened to sequential files')
    }

    // Priority 4: No torrent selected
    if (!form.selectedHash && messages.length === 0) {
      messages.push('Select a torrent to import')
    }

    return messages.join('\n')
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
