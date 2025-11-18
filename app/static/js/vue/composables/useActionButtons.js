/**
 * useActionButtons composable - Action button orchestration for common operations
 * Handles Add, Delete, Verify, and other action button logic with loading states
 */

import { ref, computed } from '../runtime.js';
import { api } from '../../core/api.js';

/**
 * Composable for "Add to qBittorrent" action
 * @param {Object} item - Item to add (search result)
 * @returns {Object} Add action state and methods
 */
export function useAddAction(item) {
  const adding = ref(false);
  const addError = ref('');
  const addSuccess = ref(false);

  const canAdd = computed(() => {
    const i = typeof item === 'object' && item.value !== undefined ? item.value : item;
    return !!(i?.dl || i?.id);
  });

  /**
   * Add torrent to qBittorrent
   */
  const performAdd = async () => {
    const i = typeof item === 'object' && item.value !== undefined ? item.value : item;

    if (!canAdd.value) {
      addError.value = 'No download link available';
      return { success: false, error: addError.value };
    }

    adding.value = true;
    addError.value = '';
    addSuccess.value = false;

    try {
      const result = await api.addTorrent({
        id: i.id,
        dl: i.dl,
        title: i.title,
        author: i.author_info || i.author,
        narrator: i.narrator_info || i.narrator
      });

      addSuccess.value = true;

      // Dispatch custom event for other components
      window.dispatchEvent(new CustomEvent('torrentAdded', {
        detail: { item: i, result }
      }));

      return { success: true, result };
    } catch (err) {
      addError.value = err.message || 'Failed to add torrent';
      return { success: false, error: addError.value };
    } finally {
      adding.value = false;
    }
  };

  /**
   * Reset add state
   */
  const resetAdd = () => {
    adding.value = false;
    addError.value = '';
    addSuccess.value = false;
  };

  return {
    adding,
    addError,
    addSuccess,
    canAdd,
    performAdd,
    resetAdd
  };
}

/**
 * Composable for "Delete" action (history items)
 * @param {Object} item - Item to delete
 * @returns {Object} Delete action state and methods
 */
export function useDeleteAction(item) {
  const deleting = ref(false);
  const deleteError = ref('');

  /**
   * Delete history item
   */
  const performDelete = async () => {
    const i = typeof item === 'object' && item.value !== undefined ? item.value : item;

    if (!i?.id) {
      deleteError.value = 'No item ID';
      return { success: false, error: deleteError.value };
    }

    deleting.value = true;
    deleteError.value = '';

    try {
      await api.deleteHistoryItem(i.id);

      // Dispatch custom event
      window.dispatchEvent(new CustomEvent('historyItemDeleted', {
        detail: { itemId: i.id }
      }));

      return { success: true };
    } catch (err) {
      deleteError.value = err.message || 'Failed to delete';
      return { success: false, error: deleteError.value };
    } finally {
      deleting.value = false;
    }
  };

  /**
   * Reset delete state
   */
  const resetDelete = () => {
    deleting.value = false;
    deleteError.value = '';
  };

  return {
    deleting,
    deleteError,
    performDelete,
    resetDelete
  };
}

/**
 * Composable for "Verify" action (Audiobookshelf verification)
 * @param {Object} item - Item to verify
 * @returns {Object} Verify action state and methods
 */
export function useVerifyAction(item) {
  const verifying = ref(false);
  const verifyError = ref('');
  const verifyResult = ref(null);

  /**
   * Verify item in Audiobookshelf
   */
  const performVerify = async () => {
    const i = typeof item === 'object' && item.value !== undefined ? item.value : item;

    if (!i?.id) {
      verifyError.value = 'No item ID';
      return { success: false, error: verifyError.value };
    }

    verifying.value = true;
    verifyError.value = '';
    verifyResult.value = null;

    try {
      const result = await api.verifyHistoryItem(i.id);
      verifyResult.value = result;

      // Dispatch custom event
      window.dispatchEvent(new CustomEvent('itemVerified', {
        detail: { itemId: i.id, result }
      }));

      return { success: true, result };
    } catch (err) {
      verifyError.value = err.message || 'Verification failed';
      return { success: false, error: verifyError.value };
    } finally {
      verifying.value = false;
    }
  };

  /**
   * Reset verify state
   */
  const resetVerify = () => {
    verifying.value = false;
    verifyError.value = '';
    verifyResult.value = null;
  };

  return {
    verifying,
    verifyError,
    verifyResult,
    performVerify,
    resetVerify
  };
}

/**
 * Composable for managing multiple action buttons at once
 * Useful for rows with multiple actions
 * @param {Object} item - Item for actions
 * @returns {Object} All action states and methods
 */
export function useRowActions(item) {
  const addAction = useAddAction(item);
  const deleteAction = useDeleteAction(item);
  const verifyAction = useVerifyAction(item);

  const anyLoading = computed(() => {
    return addAction.adding.value ||
           deleteAction.deleting.value ||
           verifyAction.verifying.value;
  });

  /**
   * Reset all actions
   */
  const resetAll = () => {
    addAction.resetAdd();
    deleteAction.resetDelete();
    verifyAction.resetVerify();
  };

  return {
    // Add action
    ...addAction,

    // Delete action
    ...deleteAction,

    // Verify action
    ...verifyAction,

    // Combined state
    anyLoading,
    resetAll
  };
}
