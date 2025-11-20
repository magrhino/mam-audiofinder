/**
 * Vue Composable for shared cover loader service
 */

import { CoverLoader } from '@services/coverLoader.js'

let sharedLoader = null
let rowCounter = 0

/**
 * Get the shared cover loader instance
 * @returns {CoverLoader} Shared cover loader
 */
export function useCoverLoader() {
  if (!sharedLoader) {
    sharedLoader = new CoverLoader()
  }
  return sharedLoader
}

/**
 * Generate unique row ID for cover loading
 * @returns {string} Unique row ID
 */
export function generateRowId() {
  return `result-row-${rowCounter++}`
}
