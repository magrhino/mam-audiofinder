/**
 * Vue Composable for authentication state management
 * Handles ABS token storage, validation, and auth flow
 *
 * Uses module-level state for singleton behavior - auth state is shared
 * across all components that use this composable.
 */

import { ref, computed, readonly } from 'vue'

const STORAGE_KEYS = {
  token: 'abs_token',
  user: 'abs_user',
  isAdmin: 'abs_is_admin',
  skipped: 'auth_skipped'
}

const sessionStore = typeof window !== 'undefined' ? window.sessionStorage : null
const legacyStore = typeof window !== 'undefined' ? window.localStorage : null

function readStoredValue(key) {
  return sessionStore?.getItem(key) ?? legacyStore?.getItem(key) ?? null
}

function writeStoredValue(key, value) {
  sessionStore?.setItem(key, value)
  legacyStore?.removeItem(key)
}

function removeStoredValue(key) {
  sessionStore?.removeItem(key)
  legacyStore?.removeItem(key)
}

const coverObjectUrls = new Map()

// Module-level singleton state (shared across all component instances)
const token = ref(readStoredValue(STORAGE_KEYS.token))
const user = ref(JSON.parse(readStoredValue(STORAGE_KEYS.user) || 'null'))
const isAdminUser = ref(readStoredValue(STORAGE_KEYS.isAdmin) === 'true')
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
  const isAdmin = computed(() => isAdminUser.value)

  /**
   * Build request headers, injecting `X-ABS-Token` when available.
   */
  function absAuthHeaders(extra = {}) {
    const headers = { ...extra }
    if (token.value) {
      headers['X-ABS-Token'] = token.value
    }
    return headers
  }

  /**
   * Build the library cover proxy URL.
   * Images can't send auth headers, so the token is appended as a query param.
   */
  function absCoverProxyUrl(absItemId) {
    if (!absItemId) return null
    return `/api/library/cover/${encodeURIComponent(absItemId)}`
  }

  async function fetchAbsCoverObjectUrl(absItemId) {
    const proxyUrl = absCoverProxyUrl(absItemId)
    if (!proxyUrl) return null

    if (coverObjectUrls.has(absItemId)) {
      return coverObjectUrls.get(absItemId)
    }

    const resp = await fetch(proxyUrl, {
      headers: absAuthHeaders(),
      cache: 'force-cache'
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const blob = await resp.blob()
    const objectUrl = URL.createObjectURL(blob)
    coverObjectUrls.set(absItemId, objectUrl)
    return objectUrl
  }

  function clearCoverObjectUrls() {
    coverObjectUrls.forEach((objectUrl) => URL.revokeObjectURL(objectUrl))
    coverObjectUrls.clear()
  }

  /**
   * Check authentication status on app initialization
   * @returns {Promise<Object|null>} Auth status or null on error
   */
  async function checkAuthStatus() {
    loading.value = true
    error.value = null

    try {
      const resp = await fetch('/api/auth/status', { headers: absAuthHeaders() })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const status = await resp.json()
      authStatus.value = { ...status, checked: true }

      // If auth required but not authenticated, clear any stale token
      if (status.requires_auth && !status.authenticated && token.value) {
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
      isAdminUser.value = data.isAdmin || false
      writeStoredValue(STORAGE_KEYS.token, data.token)
      writeStoredValue(STORAGE_KEYS.user, JSON.stringify(data.user))
      writeStoredValue(STORAGE_KEYS.isAdmin, data.isAdmin ? 'true' : 'false')

      // Update auth status
      authStatus.value.authenticated = true

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
    isAdminUser.value = false
    removeStoredValue(STORAGE_KEYS.token)
    removeStoredValue(STORAGE_KEYS.user)
    removeStoredValue(STORAGE_KEYS.isAdmin)
    clearCoverObjectUrls()
    authStatus.value.authenticated = false
  }

  /**
   * Skip authentication (when ABS not configured)
   * Sets a flag to allow access without login
   */
  function skipAuth() {
    authStatus.value.authenticated = true
    writeStoredValue(STORAGE_KEYS.skipped, 'true')
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
    isAdmin,

    // Methods
    checkAuthStatus,
    login,
    logout,
    clearAuth,
    skipAuth,
    getToken,
    absAuthHeaders,
    absCoverProxyUrl,
    fetchAbsCoverObjectUrl
  }
}
