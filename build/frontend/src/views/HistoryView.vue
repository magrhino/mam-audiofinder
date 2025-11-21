<template>
  <div class="history-view card">
    <GlassTitle>Download History & Imports</GlassTitle>
    <div class="glass-table-wrapper">
      <n-data-table
        ref="tableRef"
        :columns="columns"
        :data="enrichedHistory"
        :pagination="pagination"
        :bordered="false"
        :row-key="(row) => row.id"
        :scroll-x="scrollX"
        striped
      />
      <div v-if="!history.length" class="center muted" style="padding: 2rem;">
        No items in history yet.
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useBreakpoints } from '@vueuse/core'
import { NDataTable } from 'naive-ui'
import GlassTitle from '@components/GlassTitle.vue'
import { useHistoryLiveUpdates } from '@composables/useHistoryLiveUpdates'
import { useHistoryDataTable } from '@composables/naive/useHistoryDataTable'
import { useApi } from '@composables/useApi'

const api = useApi()

// Responsive breakpoints for dynamic scroll-x
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic scroll-x based on screen size
const scrollX = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 1400
  } else if (breakpoints.greater('tablet').value) {
    return 1200
  } else {
    return 900
  }
})

// Use the live updates composable for auto-refresh and event handling
const { history, loadHistory } = useHistoryLiveUpdates({ interval: 5000 })

// Initialize history data table
const {
  tableRef,
  columns,
  isMobile,
  enrichData,
  setAbsBaseUrl
} = useHistoryDataTable({
  onUpdated: loadHistory
})

// Enrich history data with update callback
const enrichedHistory = computed(() => enrichData(history.value))

// Pagination configuration
const pagination = ref({
  pageSize: 25,
  pageSizes: [25, 50, 100],
  showSizePicker: true,
  showQuickJumper: true
})

// Load ABS base URL on mount
onMounted(async () => {
  try {
    const config = await api.getConfig()
    setAbsBaseUrl(config.abs_base_url || '')
  } catch (err) {
    console.error('[HistoryView] Failed to load config:', err)
  }
})
</script>

<style scoped>
/* Glass table wrapper styling */
.glass-table-wrapper {
  margin-top: var(--spacing-md, 1rem);
}

/* Mobile: Optimized padding */
@media (max-width: 767px) {
  .glass-table-wrapper {
    margin-left: calc(-1 * var(--spacing-md, 1rem));
    margin-right: calc(-1 * var(--spacing-md, 1rem));
  }
}
</style>
