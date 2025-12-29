/**
 * Vue Composable for application settings management
 * Provides reactive settings state and methods for updating settings
 */

import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useApi } from './useApi'

/**
 * Composable for managing application settings
 * @returns {Object} Settings state and methods
 */
export function useSettings() {
  const api = useApi()

  // Reactive state
  const settings = reactive({
    auto_import_enabled: false,
    auto_import_flatten: true,
    auto_import_poll_interval: 30
  })

  const serviceStatus = reactive({
    running: false,
    enabled: false,
    poll_interval: 30,
    last_poll_time: null,
    pending_count: 0,
    recent_activity: []
  })

  const loading = ref(false)
  const saving = ref(false)
  const error = ref(null)
  const statusLoading = ref(false)
  let statusInterval = null

  /**
   * Load settings from backend
   */
  const loadSettings = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await api.getSettings()
      Object.assign(settings, data)
    } catch (e) {
      console.error('[useSettings] Failed to load settings:', e)
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /**
   * Save current settings to backend
   */
  const saveSettings = async () => {
    saving.value = true
    error.value = null
    try {
      await api.updateSettings({
        auto_import_enabled: settings.auto_import_enabled,
        auto_import_flatten: settings.auto_import_flatten,
        auto_import_poll_interval: settings.auto_import_poll_interval
      })
      // Reload status after settings change
      await loadServiceStatus()
      return true
    } catch (e) {
      console.error('[useSettings] Failed to save settings:', e)
      error.value = e.message
      return false
    } finally {
      saving.value = false
    }
  }

  /**
   * Reset settings to defaults
   */
  const resetToDefaults = async () => {
    saving.value = true
    error.value = null
    try {
      await api.resetSettings()
      await loadSettings()
      await loadServiceStatus()
      return true
    } catch (e) {
      console.error('[useSettings] Failed to reset settings:', e)
      error.value = e.message
      return false
    } finally {
      saving.value = false
    }
  }

  /**
   * Load auto-import service status
   */
  const loadServiceStatus = async () => {
    statusLoading.value = true
    try {
      const data = await api.getAutoImportStatus()
      Object.assign(serviceStatus, data)
    } catch (e) {
      console.error('[useSettings] Failed to load service status:', e)
    } finally {
      statusLoading.value = false
    }
  }

  /**
   * Start periodic status updates
   * @param {number} interval - Update interval in milliseconds (default: 10000)
   */
  const startStatusPolling = (interval = 10000) => {
    if (statusInterval) return
    loadServiceStatus()
    statusInterval = setInterval(loadServiceStatus, interval)
  }

  /**
   * Stop periodic status updates
   */
  const stopStatusPolling = () => {
    if (statusInterval) {
      clearInterval(statusInterval)
      statusInterval = null
    }
  }

  // Auto-cleanup on unmount
  onUnmounted(() => {
    stopStatusPolling()
  })

  return {
    // State
    settings,
    serviceStatus,
    loading,
    saving,
    error,
    statusLoading,

    // Methods
    loadSettings,
    saveSettings,
    resetToDefaults,
    loadServiceStatus,
    startStatusPolling,
    stopStatusPolling
  }
}
