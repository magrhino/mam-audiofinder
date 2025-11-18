/**
 * useApi composable - Provides access to the centralized API client
 * This is a simple wrapper around the core API client for use in Vue components
 */

import { api } from '../../core/api.js';

/**
 * Composable that provides the API client
 * @returns {Object} The centralized API client with all endpoint methods
 */
export function useApi() {
  return api;
}
