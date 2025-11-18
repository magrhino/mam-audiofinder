/**
 * useLibraryCheck composable - Check if items exist in Audiobookshelf library
 * Replaces the libraryIndicator.js component logic with Vue composition API
 */

import { ref, computed } from '../runtime.js';

/**
 * Composable for checking library status of a single item
 * @param {Object} item - Item data
 * @param {boolean} item.in_abs_library - Whether item is in library
 * @returns {Object} Library check state
 */
export function useLibraryCheck(item) {
  const inLibrary = computed(() => {
    if (typeof item === 'object' && item.value !== undefined) {
      return item.value?.in_abs_library || false;
    }
    return item?.in_abs_library || false;
  });

  const indicatorConfig = computed(() => {
    if (!inLibrary.value) {
      return null;
    }

    return {
      symbol: '✓',
      title: 'Already in your library',
      ariaLabel: 'Already in your library',
      className: 'in-library-indicator'
    };
  });

  return {
    inLibrary,
    indicatorConfig
  };
}

/**
 * Composable for batch checking library status
 * Useful for checking multiple items at once
 * @param {Array} items - Array of items to check
 * @returns {Object} Batch library check state and methods
 */
export function useBatchLibraryCheck(items) {
  const libraryMap = ref(new Map());
  const checkCount = ref(0);

  /**
   * Update library status for items
   * @param {Array} updatedItems - Items with in_abs_library property
   */
  const updateLibraryStatus = (updatedItems) => {
    if (!Array.isArray(updatedItems)) return;

    updatedItems.forEach(item => {
      const key = item.id || item.mam_id;
      if (key) {
        libraryMap.value.set(key, !!item.in_abs_library);
      }
    });

    checkCount.value = libraryMap.value.size;
  };

  /**
   * Check if a specific item is in library
   * @param {string|number} itemId - Item ID or MAM ID
   * @returns {boolean} Whether item is in library
   */
  const isInLibrary = (itemId) => {
    return libraryMap.value.get(itemId) || false;
  };

  /**
   * Get count of items in library
   * @returns {number} Count of items in library
   */
  const getLibraryCount = () => {
    let count = 0;
    for (const inLib of libraryMap.value.values()) {
      if (inLib) count++;
    }
    return count;
  };

  /**
   * Clear all library status data
   */
  const clearLibraryStatus = () => {
    libraryMap.value.clear();
    checkCount.value = 0;
  };

  const libraryCount = computed(() => getLibraryCount());

  return {
    libraryMap,
    checkCount,
    libraryCount,
    updateLibraryStatus,
    isInLibrary,
    getLibraryCount,
    clearLibraryStatus
  };
}

/**
 * Composable for verification status badges
 * @param {Object} item - Item with verification status
 * @returns {Object} Verification badge configuration
 */
export function useVerificationBadge(item) {
  const verifyStatus = computed(() => {
    if (typeof item === 'object' && item.value !== undefined) {
      return item.value?.abs_verify_status || null;
    }
    return item?.abs_verify_status || null;
  });

  const verifyNote = computed(() => {
    if (typeof item === 'object' && item.value !== undefined) {
      return item.value?.abs_verify_note || '';
    }
    return item?.abs_verify_note || '';
  });

  const badgeConfig = computed(() => {
    const status = verifyStatus.value;

    if (!status) {
      return null;
    }

    const configs = {
      'verified': {
        symbol: '✓',
        className: 'verify-badge verify-success',
        title: `Verified${verifyNote.value ? ': ' + verifyNote.value : ''}`,
        variant: 'success'
      },
      'mismatch': {
        symbol: '⚠',
        className: 'verify-badge verify-warning',
        title: `Mismatch${verifyNote.value ? ': ' + verifyNote.value : ''}`,
        variant: 'warning'
      },
      'not_found': {
        symbol: '✗',
        className: 'verify-badge verify-error',
        title: 'Not found in library',
        variant: 'error'
      },
      'unreachable': {
        symbol: '?',
        className: 'verify-badge verify-unknown',
        title: 'ABS unreachable',
        variant: 'unknown'
      },
      'not_configured': {
        symbol: '○',
        className: 'verify-badge verify-disabled',
        title: 'ABS not configured',
        variant: 'disabled'
      }
    };

    return configs[status] || null;
  });

  return {
    verifyStatus,
    verifyNote,
    badgeConfig
  };
}
