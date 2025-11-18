/**
 * @deprecated This service is deprecated in favor of the new composables.
 * Please use composables from '../composables/useCovers.js' instead:
 * - useCover() for simple cover loading
 * - useLazyCover() for lazy-loaded covers with IntersectionObserver
 * - useCoverState() for managing cover state
 *
 * This file is kept for backwards compatibility and will be removed in a future version.
 */

import { CoverLoader } from '../../services/coverLoader.js';

let sharedLoader = null;

export function useSharedCoverLoader() {
  console.warn('[DEPRECATED] useSharedCoverLoader is deprecated. Use composables from useCovers.js instead.');
  if (!sharedLoader) {
    sharedLoader = new CoverLoader();
  }
  return sharedLoader;
}
