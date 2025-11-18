<template>
  <div class="logs-view card">
    <div class="logs-header">
      <h3>Application Logs</h3>
      <div class="logs-controls">
        <select v-model="logLevel" @change="loadLogs">
          <option value="">All Levels</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
        <select v-model="logLines" @change="loadLogs">
          <option value="50">50 lines</option>
          <option value="100">100 lines</option>
          <option value="250">250 lines</option>
          <option value="500">500 lines</option>
          <option value="1000">1000 lines</option>
        </select>
        <button class="primary" @click="loadLogs">🔄 Refresh</button>
        <label>
          <input type="checkbox" v-model="autoScroll" /> Auto-scroll
        </label>
      </div>
    </div>
    <div ref="logsContainer" class="logs-container">
      <pre v-html="highlightedLogs"></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useApi } from '@composables/useApi'
import { escapeHtml } from '../../app/static/js/core/utils.js'

const api = useApi()
const logLevel = ref('')
const logLines = ref('100')
const autoScroll = ref(true)
const highlightedLogs = ref('Loading logs...')
const logsContainer = ref(null)

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
/* Uses main.css styles */
</style>
