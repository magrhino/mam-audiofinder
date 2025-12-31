/**
 * Vue Composable for authentication state management
 * Handles ABS token storage, validation, and auth flow
 *
 * Uses module-level state for singleton behavior - auth state is shared
 * across all components that use this composable.
 */

import { ref, computed, readonly } from 'vue'

// Module-level singleton state (shared across all component instances)
const token = ref(localStorage.getItem('abs_token') || null)
const user = ref(JSON.parse(localStorage.getItem('abs_user') || 'null'))
const authStatus = ref({
  requires_auth: false,
  abs_configured: false,
  abs_url: null,
  authenticated: false,
  checked: false
})
const loading = ref(false)
const error = ref(null)

/**
 * Composable for authentication
 * @returns {Object} Auth state and methods
 */
export function useAuth() {
  // Computed properties
  const isAuthenticated = computed(() => {
    // If auth not required, always authenticated
    if (!authStatus.value.requires_auth) return true
    // Otherwise, need valid token and confirmed authentication
    return !!token.value && authStatus.value.authenticated
  })

  const requiresAuth = computed(() => authStatus.value.requires_auth)
  const absConfigured = computed(() => authStatus.value.abs_configured)
  const absUrl = computed(() => authStatus.value.abs_url)

  /**
   * Check authentication status on app initialization
   * @returns {Promise<Object|null>} Auth status or null on error
   */
  async function checkAuthStatus() {
    loading.value = true
    error.value = null

    try {
      const headers = {}
      if (token.value) {
        headers['X-ABS-Token'] = token.value
      }

      const resp = await fetch('/api/auth/status', { headers })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const status = await resp.json()
      authStatus.value = { ...status, checked: true }

      // If auth required but not authenticated, clear any stale token
      if (status.requires_auth && !status.authenticated && token.value) {
        console.log('[useAuth] Token invalid, clearing')
        clearAuth()
      }

      return status
    } catch (e) {
      console.error('[useAuth] Failed to check status:', e)
      error.value = e.message
      authStatus.value.checked = true
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Login with ABS credentials
   * @param {string} username - Username
   * @param {string} password - Password
   * @returns {Promise<boolean>} True if login successful
   */
  async function login(username, password) {
    loading.value = true
    error.value = null

    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password
        })
      })

      const data = await resp.json()

      if (!data.ok) {
        error.value = data.error || 'Login failed'
        return false
      }

      // Store token and user info
      token.value = data.token
      user.value = data.user
      localStorage.setItem('abs_token', data.token)
      localStorage.setItem('abs_user', JSON.stringify(data.user))

      // Update auth status
      authStatus.value.authenticated = true

      console.log('[useAuth] Login successful')
      return true
    } catch (e) {
      console.error('[useAuth] Login error:', e)
      error.value = e.message
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Logout - clear stored credentials
   */
  async function logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch (e) {
      console.warn('[useAuth] Logout request failed:', e)
    }

    clearAuth()
  }

  /**
   * Clear auth state (internal use)
   */
  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('abs_token')
    localStorage.removeItem('abs_user')
    authStatus.value.authenticated = false
  }

  /**
   * Skip authentication (when ABS not configured)
   * Sets a flag to allow access without login
   */
  function skipAuth() {
    authStatus.value.authenticated = true
    localStorage.setItem('auth_skipped', 'true')
  }

  /**
   * Get token for API requests
   * @returns {string|null} Current token
   */
  function getToken() {
    return token.value
  }

  return {
    // State (readonly to prevent external mutation)
    token: readonly(token),
    user: readonly(user),
    authStatus: readonly(authStatus),
    loading: readonly(loading),
    error,  // error is writable for clearing

    // Computed
    isAuthenticated,
    requiresAuth,
    absConfigured,
    absUrl,

    // Methods
    checkAuthStatus,
    login,
    logout,
    clearAuth,
    skipAuth,
    getToken
  }
}
