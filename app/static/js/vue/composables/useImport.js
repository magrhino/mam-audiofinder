/**
 * useImport composable - Vue-reactive import workflow logic
 * Replaces the class-based ImportForm with composition API
 */

import { ref, reactive, computed, watch } from '../runtime.js';
import { api } from '../../core/api.js';

/**
 * Composable for import workflow (torrents to library)
 * @param {Object} historyItem - History item to import
 * @returns {Object} Import state and methods
 */
export function useImport(historyItem) {
  const loading = ref(false);
  const torrents = ref([]);
  const torrentTree = ref(null);
  const statusMessage = ref('');
  const buttonLabel = ref('Copy to Library');
  const formLoaded = ref(false);
  const showTree = ref(false);

  const form = reactive({
    author: historyItem?.author || '',
    title: historyItem?.title || '',
    selectedHash: historyItem?.qb_hash || '',
    flatten: false
  });

  /**
   * Load configuration and torrents
   */
  const loadFormData = async () => {
    if (formLoaded.value) return;

    formLoaded.value = true;
    loading.value = true;
    statusMessage.value = '';

    try {
      // Fetch import mode configuration
      const cfg = await api.getConfig();
      if (cfg.import_mode === 'link') {
        buttonLabel.value = 'Link to Library';
      } else if (cfg.import_mode === 'move') {
        buttonLabel.value = 'Move to Library';
      }
    } catch (err) {
      console.warn('Failed to fetch config', err);
    }

    try {
      // Fetch completed torrents
      const data = await api.getCompletedTorrents();
      torrents.value = data.items || [];

      // Auto-select matching torrent
      if (!form.selectedHash && historyItem) {
        const match = torrents.value.find(t =>
          t.hash === historyItem.qb_hash ||
          String(t.mam_id || '') === String(historyItem.mam_id || '')
        );

        if (match) {
          form.selectedHash = match.hash;
          statusMessage.value = '✓ Auto-selected matching torrent';
        }
      }
    } catch (err) {
      console.error('Failed to load torrents', err);
      statusMessage.value = 'Failed to load torrents';
    } finally {
      loading.value = false;
    }
  };

  /**
   * Load torrent file tree for preview
   */
  const loadTorrentTree = async (hash) => {
    if (!hash) {
      torrentTree.value = null;
      showTree.value = false;
      return;
    }

    loading.value = true;
    try {
      const data = await api.getTorrentTree(hash);
      torrentTree.value = data;
      showTree.value = true;
    } catch (err) {
      console.error('Failed to load torrent tree', err);
      statusMessage.value = 'Failed to load file tree';
      torrentTree.value = null;
      showTree.value = false;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Perform the import
   */
  const performImport = async () => {
    if (!form.selectedHash) {
      statusMessage.value = 'Select a torrent to import';
      return { success: false, message: 'No torrent selected' };
    }

    if (!form.author || !form.title) {
      statusMessage.value = 'Author and title are required';
      return { success: false, message: 'Missing required fields' };
    }

    loading.value = true;
    statusMessage.value = 'Importing…';

    try {
      const result = await api.importTorrent({
        author: form.author,
        title: form.title,
        hash: form.selectedHash,
        history_id: historyItem?.id,
        flatten: form.flatten
      });

      statusMessage.value = '✓ Import requested';
      return { success: true, result };
    } catch (err) {
      const message = `Import failed: ${err.message}`;
      statusMessage.value = message;
      return { success: false, message, error: err };
    } finally {
      loading.value = false;
    }
  };

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    form.author = historyItem?.author || '';
    form.title = historyItem?.title || '';
    form.selectedHash = historyItem?.qb_hash || '';
    form.flatten = false;
    statusMessage.value = '';
    torrentTree.value = null;
    showTree.value = false;
  };

  // Computed properties
  const selectedTorrent = computed(() => {
    return torrents.value.find(t => t.hash === form.selectedHash);
  });

  const hasMultiDisc = computed(() => {
    return torrentTree.value?.has_multi_disc || false;
  });

  const canImport = computed(() => {
    return !loading.value &&
           form.selectedHash &&
           form.author &&
           form.title;
  });

  // Watch for torrent selection changes
  watch(() => form.selectedHash, (newHash) => {
    if (newHash) {
      loadTorrentTree(newHash);
    } else {
      torrentTree.value = null;
      showTree.value = false;
    }
  });

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

    // Methods
    loadFormData,
    loadTorrentTree,
    performImport,
    resetForm
  };
}

/**
 * Composable for verifying imported items in Audiobookshelf
 * @returns {Object} Verification state and methods
 */
export function useVerification() {
  const verifying = ref(false);
  const verificationResult = ref(null);

  /**
   * Verify a history item against Audiobookshelf library
   * @param {number} historyId - History item ID
   */
  const verifyItem = async (historyId) => {
    verifying.value = true;
    verificationResult.value = null;

    try {
      const result = await api.verifyHistoryItem(historyId);
      verificationResult.value = result;
      return { success: true, result };
    } catch (err) {
      const error = `Verification failed: ${err.message}`;
      verificationResult.value = { error };
      return { success: false, error: err };
    } finally {
      verifying.value = false;
    }
  };

  /**
   * Clear verification result
   */
  const clearResult = () => {
    verificationResult.value = null;
  };

  return {
    verifying,
    verificationResult,
    verifyItem,
    clearResult
  };
}
