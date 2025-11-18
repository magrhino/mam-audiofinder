/**
 * useCovers composable - Vue-reactive cover loading with lazy loading
 * Replaces the class-based CoverLoader with a Vue composition API approach
 */

import { ref, onMounted, onUnmounted, reactive } from '../runtime.js';
import { api } from '../../core/api.js';

// Shared IntersectionObserver instance
let sharedObserver = null;
let observerRefCount = 0;

/**
 * Initialize the shared IntersectionObserver
 */
function initSharedObserver() {
  if (!sharedObserver) {
    console.log('[useLazyCover] Creating new shared IntersectionObserver');
    sharedObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        console.log('[useLazyCover] Observer callback:', {
          isIntersecting: entry.isIntersecting,
          target: entry.target,
          hasFetchFn: !!entry.target._coverFetchFn
        });
        if (entry.isIntersecting) {
          const container = entry.target;
          const fetchFn = container._coverFetchFn;

          // Stop observing immediately to avoid duplicate fetches
          sharedObserver.unobserve(container);

          if (fetchFn) {
            console.log('[useLazyCover] Calling fetchFn for element');
            fetchFn();
          } else {
            console.warn('[useLazyCover] Element has no _coverFetchFn attached!');
          }
        }
      });
    }, {
      rootMargin: '50px',
      threshold: 0.01
    });
  }
  observerRefCount++;
  console.log('[useLazyCover] Observer refCount:', observerRefCount);
  return sharedObserver;
}

/**
 * Clean up the shared observer when no longer needed
 */
function cleanupSharedObserver() {
  observerRefCount--;
  if (observerRefCount <= 0 && sharedObserver) {
    sharedObserver.disconnect();
    sharedObserver = null;
    observerRefCount = 0;
  }
}

/**
 * Composable for loading a single cover image
 * @param {Object} params - Cover parameters
 * @param {string} params.mamId - MAM torrent ID
 * @param {string} params.title - Book title
 * @param {string} params.author - Author name
 * @returns {Object} Cover loading state and methods
 */
export function useCover({ mamId, title, author }) {
  const coverUrl = ref('');
  const itemId = ref('');
  const loading = ref(false);
  const error = ref('');
  const loaded = ref(false);

  /**
   * Fetch cover from backend
   */
  const fetchCover = async () => {
    if (!mamId || !title) {
      error.value = 'Missing required info';
      return;
    }

    loading.value = true;
    error.value = '';

    try {
      const data = await api.fetchCover({
        mam_id: mamId,
        title: title,
        author: author || '',
        max_retries: '2'
      });

      if (data.cover_url) {
        coverUrl.value = data.cover_url;
        itemId.value = data.item_id || '';
        loaded.value = true;
      } else {
        error.value = data.error || 'No cover found';
      }
    } catch (e) {
      console.error('Cover fetch exception:', e);
      error.value = 'Failed to load cover';
    } finally {
      loading.value = false;
    }
  };

  return {
    coverUrl,
    itemId,
    loading,
    error,
    loaded,
    fetchCover
  };
}

/**
 * Composable for lazy-loading cover images using IntersectionObserver
 * @param {Object} params - Cover parameters
 * @param {Ref<string>} params.mamId - MAM torrent ID (reactive)
 * @param {Ref<string>} params.title - Book title (reactive)
 * @param {Ref<string>} params.author - Author name (reactive)
 * @param {Ref<HTMLElement>} params.elementRef - DOM element ref to observe
 * @returns {Object} Cover loading state
 */
export function useLazyCover({ mamId, title, author, elementRef }) {
  const coverUrl = ref('');
  const itemId = ref('');
  const loading = ref(false);
  const error = ref('');
  const loaded = ref(false);
  let observer = null;

  /**
   * Fetch cover from backend
   */
  const fetchCover = async () => {
    const id = typeof mamId === 'object' && mamId.value !== undefined ? mamId.value : mamId;
    const t = typeof title === 'object' && title.value !== undefined ? title.value : title;
    const a = typeof author === 'object' && author.value !== undefined ? author.value : author;

    console.log('[useLazyCover] fetchCover called:', { id, title: t, author: a });

    if (!id || !t) {
      error.value = 'Missing info';
      console.warn('[useLazyCover] Missing required data for cover fetch');
      return;
    }

    loading.value = true;
    error.value = '';

    try {
      console.log('[useLazyCover] Calling api.fetchCover...');
      const data = await api.fetchCover({
        mam_id: id,
        title: t,
        author: a || '',
        max_retries: '2'
      });

      console.log('[useLazyCover] api.fetchCover response:', data);

      if (data.cover_url) {
        coverUrl.value = data.cover_url;
        itemId.value = data.item_id || '';
        loaded.value = true;
        console.log('[useLazyCover] Cover loaded successfully:', data.cover_url);
      } else {
        error.value = data.error || 'No cover';
        console.log('[useLazyCover] No cover found:', data.error);
      }
    } catch (e) {
      console.error('[useLazyCover] Cover fetch exception:', e);
      error.value = 'Error';
    } finally {
      loading.value = false;
    }
  };

  /**
   * Start observing the element
   */
  const startObserving = () => {
    const el = typeof elementRef === 'object' && elementRef.value !== undefined
      ? elementRef.value
      : elementRef;

    console.log('[useLazyCover] startObserving called, el:', el, 'mamId:',
      typeof mamId === 'object' ? mamId.value : mamId);

    if (!el) {
      console.warn('[useLazyCover] No element to observe!');
      return;
    }

    observer = initSharedObserver();

    // Attach fetch function to element for observer callback
    el._coverFetchFn = fetchCover;

    console.log('[useLazyCover] Starting to observe element');
    observer.observe(el);
  };

  /**
   * Stop observing
   */
  const stopObserving = () => {
    const el = typeof elementRef === 'object' && elementRef.value !== undefined
      ? elementRef.value
      : elementRef;

    if (observer && el) {
      observer.unobserve(el);
      delete el._coverFetchFn;
    }
  };

  onMounted(() => {
    startObserving();
  });

  onUnmounted(() => {
    stopObserving();
    cleanupSharedObserver();
  });

  return {
    coverUrl,
    itemId,
    loading,
    error,
    loaded,
    fetchCover,
    startObserving,
    stopObserving
  };
}

/**
 * Composable for managing cover state with manual updates
 * Useful when cover data comes from props or external sources
 * @param {Object} initialData - Initial cover data
 * @returns {Object} Cover state
 */
export function useCoverState(initialData = {}) {
  const state = reactive({
    coverUrl: initialData.coverUrl || initialData.abs_cover_url || '',
    itemId: initialData.itemId || initialData.abs_item_id || '',
    localFile: initialData.local_file || '',
    loaded: !!initialData.coverUrl || !!initialData.abs_cover_url
  });

  const updateCover = (data) => {
    if (data.coverUrl || data.cover_url) {
      state.coverUrl = data.coverUrl || data.cover_url;
      state.loaded = true;
    }
    if (data.itemId || data.item_id) {
      state.itemId = data.itemId || data.item_id;
    }
    if (data.local_file) {
      state.localFile = data.local_file;
    }
  };

  return {
    ...state,
    updateCover
  };
}
