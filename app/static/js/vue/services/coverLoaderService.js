import { CoverLoader } from '../../services/coverLoader.js';

let sharedLoader = null;

export function useSharedCoverLoader() {
  if (!sharedLoader) {
    sharedLoader = new CoverLoader();
  }
  return sharedLoader;
}
