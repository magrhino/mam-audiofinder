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
import { NSwitch, NInputNumber, NButton, NAlert, NDataTable, NTag } from 'naive-ui'
import { useSettings } from '@composables/useSettings'
import { useApi } from '@composables/useApi'

const api = useApi()
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
    width: 100,
    render: (row) => {
      const typeMap = {
        completed: 'success',
        failed: 'error',
        skipped: 'warning',
        processing: 'info',
        pending: 'default'
      }
      return h(NTag, { type: typeMap[row.status] || 'default', size: 'small' }, () => row.status)
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

const handleSave = async () => {
  const success = await saveSettings()
  if (success) {
    // Could show a success notification here
    console.log('[SettingsView] Settings saved successfully')
  }
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
    loadServiceStatus()
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
