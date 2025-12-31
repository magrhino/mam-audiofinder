<template>
  <div class="settings-view w-full max-w-full overflow-x-hidden">
    <h2 class="heading-1 mb-6">Settings</h2>

    <!-- Auto-Import Section -->
    <section class="glass-panel p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4">Auto-Import</h3>
      <p class="muted mb-4">
        Automatically import completed torrents to your library. Only single-book torrents are auto-imported;
        multi-book torrents (series boxes, bundles) are skipped and require manual import.
      </p>

      <div class="settings-grid">
        <div class="settings-row">
          <div class="settings-label">
            <label>Enable Auto-Import</label>
            <span class="settings-description">Automatically import completed torrents</span>
          </div>
          <n-switch
            v-model:value="settings.auto_import_enabled"
            :disabled="saving"
          />
        </div>

        <div class="settings-row">
          <div class="settings-label">
            <label>Flatten Multi-Disc</label>
            <span class="settings-description">Flatten multi-disc structure to sequential files during auto-import</span>
          </div>
          <n-switch
            v-model:value="settings.auto_import_flatten"
            :disabled="saving"
          />
        </div>

        <div class="settings-row">
          <div class="settings-label">
            <label>Poll Interval</label>
            <span class="settings-description">How often to check for completed torrents (15-300 seconds)</span>
          </div>
          <n-input-number
            v-model:value="settings.auto_import_poll_interval"
            :min="15"
            :max="300"
            :step="5"
            :disabled="saving"
            style="width: 120px"
          />
        </div>
      </div>

      <div class="settings-actions mt-4">
        <n-button type="primary" @click="handleSave" :loading="saving" :disabled="loading">
          Save Changes
        </n-button>
        <n-button @click="handleReset" :loading="saving" :disabled="loading">
          Reset to Defaults
        </n-button>
      </div>

      <n-alert v-if="error" type="error" class="mt-4" closable @close="error = null">
        {{ error }}
      </n-alert>
    </section>

    <!-- Import Settings Section -->
    <section class="glass-panel p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4">Import Settings</h3>
      <p class="muted mb-4">
        Configure how files are imported to your library.
      </p>

      <div class="settings-grid">
        <div class="settings-row">
          <div class="settings-label">
            <label>Cover Source Priority</label>
            <span class="settings-description">Which cover image to use when importing</span>
          </div>
          <n-select
            v-model:value="settings.cover_source_priority"
            :options="coverPriorityOptions"
            :disabled="saving"
            style="width: 180px"
          />
        </div>
      </div>

      <div class="settings-actions mt-4">
        <n-button type="primary" @click="handleSave" :loading="saving" :disabled="loading">
          Save Changes
        </n-button>
      </div>
    </section>

    <!-- Libraries Section (Admin Only) -->
    <section v-if="isAdmin" class="glass-panel p-6 mb-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Libraries</h3>
        <n-button size="small" @click="refreshLibraries" :loading="librariesLoading">
          Refresh
        </n-button>
      </div>
      <p class="muted mb-4">
        Select which Audiobookshelf libraries to search. Only audiobook libraries (mediaType: book) are shown.
      </p>

      <n-alert v-if="!config.abs_configured" type="warning" class="mb-4">
        Audiobookshelf is not configured. Set ABS_BASE_URL environment variable.
      </n-alert>

      <div v-else-if="librariesLoading && libraries.length === 0" class="text-gray-400">
        Loading libraries...
      </div>

      <div v-else-if="libraries.length === 0" class="text-gray-400">
        No libraries found. Make sure you have access to libraries in Audiobookshelf.
      </div>

      <div v-else class="settings-grid">
        <div v-for="lib in libraries" :key="lib.id" class="settings-row">
          <div class="settings-label">
            <label>{{ lib.name }}</label>
            <span class="settings-description">
              {{ lib.media_type === 'book' ? 'Audiobooks' : lib.media_type }}
            </span>
          </div>
          <n-switch
            :value="lib.enabled"
            @update:value="(val) => toggleLibrary(lib.id, val)"
            :disabled="librariesSaving"
          />
        </div>
      </div>

      <n-alert v-if="librariesError" type="error" class="mt-4" closable @close="librariesError = null">
        {{ librariesError }}
      </n-alert>
    </section>

    <!-- Service Status Section -->
    <section class="glass-panel p-6 mb-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">Auto-Import Status</h3>
        <n-button size="small" @click="loadServiceStatus" :loading="statusLoading">
          Refresh
        </n-button>
      </div>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">Service Status</span>
          <span :class="['status-value', serviceStatus.running ? 'text-green-400' : 'text-red-400']">
            {{ serviceStatus.running ? 'Running' : 'Stopped' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">Auto-Import</span>
          <span :class="['status-value', serviceStatus.enabled ? 'text-green-400' : 'text-gray-400']">
            {{ serviceStatus.enabled ? 'Enabled' : 'Disabled' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">Poll Interval</span>
          <span class="status-value">{{ serviceStatus.poll_interval }}s</span>
        </div>
        <div class="status-item">
          <span class="status-label">Pending Items</span>
          <span class="status-value">{{ serviceStatus.pending_count }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Last Poll</span>
          <span class="status-value">{{ formatLastPoll(serviceStatus.last_poll_time) }}</span>
        </div>
      </div>

      <!-- Recent Activity -->
      <div v-if="serviceStatus.recent_activity?.length > 0" class="mt-4">
        <h4 class="text-sm font-medium mb-2">Recent Activity</h4>
        <n-data-table
          :columns="activityColumns"
          :data="serviceStatus.recent_activity"
          :bordered="false"
          size="small"
          :single-line="false"
        />
      </div>
      <div v-else class="mt-4 text-gray-400 text-sm">
        No recent auto-import activity
      </div>
    </section>

    <!-- Environment Settings Section (Read-only) -->
    <section class="glass-panel p-6">
      <h3 class="text-lg font-semibold mb-4">Environment Settings</h3>
      <p class="muted mb-4">
        These settings are configured via environment variables and require a container restart to change.
      </p>

      <div class="settings-grid readonly">
        <div class="settings-row">
          <div class="settings-label">
            <label>Import Mode</label>
            <span class="settings-description">How files are transferred to library</span>
          </div>
          <span class="settings-readonly-value">{{ config.import_mode || 'link' }}</span>
        </div>
        <div class="settings-row">
          <div class="settings-label">
            <label>Default Flatten</label>
            <span class="settings-description">Default disc flattening behavior</span>
          </div>
          <span class="settings-readonly-value">{{ config.flatten_discs ? 'Yes' : 'No' }}</span>
        </div>
        <div class="settings-row">
          <div class="settings-label">
            <label>Audiobookshelf</label>
            <span class="settings-description">ABS integration status</span>
          </div>
          <span :class="['settings-readonly-value', config.abs_configured ? 'text-green-400' : 'text-gray-400']">
            {{ config.abs_configured ? 'Configured' : 'Not Configured' }}
          </span>
        </div>
        <div class="settings-row">
          <div class="settings-label">
            <label>Hardcover</label>
            <span class="settings-description">Hardcover API status</span>
          </div>
          <span :class="['settings-readonly-value', config.hardcover_configured ? 'text-green-400' : 'text-gray-400']">
            {{ config.hardcover_configured ? 'Configured' : 'Not Configured' }}
          </span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, h } from 'vue'
import { NSwitch, NInputNumber, NButton, NAlert, NDataTable, NTag, NSelect, NTooltip } from 'naive-ui'
import { useSettings } from '@composables/useSettings'
import { useApi } from '@composables/useApi'
import { useAuth } from '@composables/useAuth'

const api = useApi()
const { isAdmin, absAuthHeaders } = useAuth()
const {
  settings,
  serviceStatus,
  loading,
  saving,
  error,
  statusLoading,
  loadSettings,
  saveSettings,
  resetToDefaults,
  loadServiceStatus,
  startStatusPolling,
  stopStatusPolling
} = useSettings()

// Cover source priority options
const coverPriorityOptions = [
  { label: 'Torrent (Default)', value: 'torrent' },
  { label: 'Shelfarr Cache', value: 'shelfarr' }
]

// Libraries state (Admin only)
const libraries = ref([])
const librariesLoading = ref(false)
const librariesSaving = ref(false)
const librariesError = ref(null)

// App config (read-only from /config endpoint)
const config = reactive({
  import_mode: '',
  flatten_discs: false,
  abs_configured: false,
  hardcover_configured: false
})

// Activity table columns
const activityColumns = [
  {
    title: 'Title',
    key: 'title',
    ellipsis: true,
    render: (row) => row.title || 'Unknown'
  },
  {
    title: 'Status',
    key: 'status',
    width: 120,
    render: (row) => {
      const typeMap = {
        completed: 'success',
        failed: 'error',
        skipped: 'warning',
        processing: 'info',
        pending: 'default'
      }
      const tagType = typeMap[row.status] || 'default'

      // Show retry count for failed items
      if (row.status === 'failed' && row.retry_count > 0) {
        return h('div', { class: 'flex flex-col gap-1' }, [
          h(NTag, { type: tagType, size: 'small' }, () => row.status),
          h('span', { class: 'text-xs text-gray-400' }, `Retry ${row.retry_count}/5`)
        ])
      }

      return h(NTag, { type: tagType, size: 'small' }, () => row.status)
    }
  },
  {
    title: 'Details',
    key: 'last_error',
    ellipsis: true,
    render: (row) => {
      // Show error message for failed items
      if (row.status === 'failed' && (row.last_error || row.reason)) {
        const errorMsg = row.last_error || row.reason
        return h(NTooltip, { trigger: 'hover' }, {
          default: () => errorMsg,
          trigger: () => h('span', { class: 'text-red-400 text-sm truncate block max-w-[200px]' }, errorMsg)
        })
      }
      // Show skip reason
      if (row.status === 'skipped' && row.reason) {
        return h(NTooltip, { trigger: 'hover' }, {
          default: () => row.reason,
          trigger: () => h('span', { class: 'text-yellow-400 text-sm truncate block max-w-[200px]' }, row.reason)
        })
      }
      return '-'
    }
  },
  {
    title: 'Time',
    key: 'attempted_at',
    width: 140,
    render: (row) => formatTime(row.attempted_at)
  }
]

const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    Object.assign(config, data)
  } catch (e) {
    console.error('[SettingsView] Failed to load config:', e)
  }
}

// Load libraries from ABS
const loadLibraries = async () => {
  if (!isAdmin.value) return

  librariesLoading.value = true
  librariesError.value = null

  try {
    const resp = await fetch('/api/abs/libraries', {
      headers: absAuthHeaders()
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const data = await resp.json()
    libraries.value = data.libraries || []
  } catch (e) {
    console.error('[SettingsView] Failed to load libraries:', e)
    librariesError.value = e.message
  } finally {
    librariesLoading.value = false
  }
}

// Refresh libraries from ABS
const refreshLibraries = async () => {
  librariesLoading.value = true
  librariesError.value = null

  try {
    // First refresh from ABS
    const refreshResp = await fetch('/api/abs/libraries/refresh', {
      method: 'POST',
      headers: absAuthHeaders()
    })

    if (!refreshResp.ok) {
      throw new Error(`HTTP ${refreshResp.status}`)
    }

    // Then reload the list
    await loadLibraries()
  } catch (e) {
    console.error('[SettingsView] Failed to refresh libraries:', e)
    librariesError.value = e.message
    librariesLoading.value = false
  }
}

// Toggle library enabled state
const toggleLibrary = async (libraryId, enabled) => {
  librariesSaving.value = true
  librariesError.value = null

  try {
    // Get current enabled IDs and update
    const currentEnabled = libraries.value
      .filter(lib => lib.enabled)
      .map(lib => lib.id)

    let newEnabled
    if (enabled) {
      newEnabled = [...currentEnabled, libraryId]
    } else {
      newEnabled = currentEnabled.filter(id => id !== libraryId)
    }

    const resp = await fetch('/api/abs/libraries', {
      method: 'PUT',
      headers: absAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ enabled_library_ids: newEnabled })
    })

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    // Update local state
    const lib = libraries.value.find(l => l.id === libraryId)
    if (lib) {
      lib.enabled = enabled
    }

  } catch (e) {
    console.error('[SettingsView] Failed to toggle library:', e)
    librariesError.value = e.message
  } finally {
    librariesSaving.value = false
  }
}

const handleSave = async () => {
  await saveSettings()
}


const handleReset = async () => {
  if (confirm('Reset all settings to their default values?')) {
    await resetToDefaults()
  }
}

const formatLastPoll = (timestamp) => {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  const now = new Date()
  const diffSec = Math.floor((now - date) / 1000)
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  return date.toLocaleTimeString()
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString()
}

onMounted(async () => {
  await Promise.all([
    loadSettings(),
    loadConfig(),
    loadServiceStatus(),
    loadLibraries()  // Load libraries if admin
  ])
  // Start polling status every 10 seconds
  startStatusPolling(10000)
})

onUnmounted(() => {
  stopStatusPolling()
})
</script>

<style scoped>
.settings-view {
  max-width: 800px;
  margin: 0 auto;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.settings-row:last-child {
  border-bottom: none;
}

.settings-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.settings-label label {
  font-weight: 500;
  color: var(--text-primary);
}

.settings-description {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.settings-readonly-value {
  font-family: monospace;
  color: var(--text-secondary);
}

.settings-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--spacing-md);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.status-value {
  font-size: 1rem;
  font-weight: 500;
}

/* Mobile responsive */
@media (max-width: 767px) {
  .settings-row {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .settings-actions {
    flex-direction: column;
  }

  .settings-actions :deep(.n-button) {
    width: 100%;
  }
}
</style>
