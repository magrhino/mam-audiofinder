/**
 * Vue Composable for API access
 * Provides access to the centralized API client
 */

import { api } from '../../app/static/js/core/api.js'

/**
 * Composable for accessing the API client
 * @returns {Object} API client instance
 */
export function useApi() {
  return api
}
