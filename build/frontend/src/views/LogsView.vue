<template>
  <div class="logs-view card w-full max-w-full overflow-x-hidden">
    <div class="logs-header">
      <h3>Application Logs</h3>
      <div class="logs-controls">
        <n-select v-model:value="logLevel" @update:value="loadLogs" :options="levelOptions" placeholder="All Levels" style="width: 140px" />
        <n-select v-model:value="logLines" @update:value="loadLogs" :options="linesOptions" style="width: 120px" />
        <n-button type="primary" @click="loadLogs">🔄 Refresh</n-button>
        <n-checkbox v-model:checked="autoScroll">Auto-scroll</n-checkbox>
      </div>
    </div>
    <div ref="logsContainer" class="logs-container">
      <pre v-html="highlightedLogs"></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { NSelect, NButton, NCheckbox } from 'naive-ui'
import { useApi } from '@composables/useApi'
import { escapeHtml } from '@core/utils.js'

const api = useApi()
const logLevel = ref('')
const logLines = ref('100')
const autoScroll = ref(true)
const highlightedLogs = ref('Loading logs...')
const logsContainer = ref(null)

const levelOptions = [
  { label: 'All Levels', value: '' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' }
]

const linesOptions = [
  { label: '50 lines', value: '50' },
  { label: '100 lines', value: '100' },
  { label: '250 lines', value: '250' },
  { label: '500 lines', value: '500' },
  { label: '1000 lines', value: '1000' }
]

const highlightLogs = (text) => {
  return escapeHtml(text)
    .replace(/\b(INFO)\b/g, '<span class="log-info">$1</span>')
    .replace(/\b(WARNING)\b/g, '<span class="log-warning">$1</span>')
    .replace(/\b(ERROR)\b/g, '<span class="log-error">$1</span>')
}

const loadLogs = async () => {
  try {
    highlightedLogs.value = 'Loading logs...'

    const data = await api.getLogs({
      lines: parseInt(logLines.value, 10),
      level: logLevel.value
    })

    if (!data.ok) {
      highlightedLogs.value = `Error: ${data.error || 'Unknown error'}`
      return
    }

    if (!data.logs || data.logs.length === 0) {
      highlightedLogs.value = 'No logs found.'
      return
    }

    // Display logs with syntax highlighting
    const logsText = data.logs.join('')
    highlightedLogs.value = highlightLogs(logsText)

    // Auto-scroll to bottom if enabled
    if (autoScroll.value) {
      await nextTick()
      if (logsContainer.value) {
        logsContainer.value.scrollTop = logsContainer.value.scrollHeight
      }
    }
  } catch (error) {
    console.error('Error loading logs:', error)
    highlightedLogs.value = `Error loading logs: ${error.message}`
  }
}

onMounted(() => {
  loadLogs()
})

// Watch for changes to auto-scroll logs when they update
watch(highlightedLogs, async () => {
  if (autoScroll.value) {
    await nextTick()
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  }
})
</script>

<style scoped>
.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.logs-controls {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-wrap: wrap;
}

.logs-container {
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  max-height: 600px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

.logs-container pre {
  margin: 0;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.4;
}

/* Syntax highlighting for log levels */
:deep(.log-info) {
  color: #6ab7ff;
}

:deep(.log-warning) {
  color: var(--warning);
}

:deep(.log-error) {
  color: var(--error);
}

/* Responsive adjustments - mobile breakpoint (0-767px) */
@media (max-width: 767px) {
  .logs-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .logs-controls {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .logs-controls :deep(.n-select),
  .logs-controls :deep(.n-button) {
    width: 100%;
  }

  .logs-container {
    max-height: 400px;
  }
}
</style>
