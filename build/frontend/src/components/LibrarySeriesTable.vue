<script setup>
import { h, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NDataTable, NTag, NImage, NButton, NScrollbar } from 'naive-ui'
import SeriesCompletionRing from '@/components/SeriesCompletionRing.vue'
import HardcoverLinkBadge from '@/components/HardcoverLinkBadge.vue'
import MissingBooksPopover from '@/components/MissingBooksPopover.vue'
import SeriesActionsDropdown from '@/components/SeriesActionsDropdown.vue'
import ExpandedSeriesContent from '@/components/ExpandedSeriesContent.vue'
import { useBreakpoints } from '@/composables/useBreakpoints'

const props = defineProps({
  series: { type: Array, required: true },
})

const emit = defineEmits(['diff', 'editLink', 'refresh', 'addToWishlist', 'search'])
const router = useRouter()
const { isMobile, isTablet } = useBreakpoints()

// Track expanded rows for book preview
const expandedRowKeys = ref([])

function handleExpand(keys) {
  expandedRowKeys.value = keys
}

// Column definitions
const columns = computed(() => {
  const cols = [
    // Expand column for row expansion (always visible)
    {
      type: 'expand',
      expandable: () => true,
      renderExpand: (row) => renderExpandedRow(row),
    },
    // Completion Ring column
    {
      title: '',
      key: 'completion',
      width: 50,
      align: 'center',
      render: (row) => h(SeriesCompletionRing, {
        percentage: row.completion_percentage ?? 100,
        owned: row.abs_book_count ?? row.book_count ?? 0,
        total: row.series_book_count ?? row.book_count ?? 0,
        size: 32,
      }),
    },
    // Series name with inline missing indicator
    {
      title: 'Series',
      key: 'name',
      sorter: 'default',
      render: (row) => h('div', { class: 'series-cell' }, [
        h('div', { class: 'series-name' }, row.name),
        h(MissingBooksPopover, {
          count: row.missing_count ?? 0,
          seriesName: row.name,
          hardcoverSeriesId: row.hardcover_series_id,
          onExpand: () => emit('diff', row.name, row.hardcover_series_id),
          onAddToWishlist: (book) => emit('addToWishlist', book),
        }),
      ]),
    },
  ]

  // Add author column on tablet+
  if (!isMobile.value) {
    cols.push({
      title: 'Author',
      key: 'author',
      width: 180,
      ellipsis: { tooltip: true },
    })
  }

  // Progress column (always visible)
  cols.push({
    title: 'Progress',
    key: 'progress',
    width: 90,
    align: 'center',
    render: (row) => {
      const absCount = row.abs_book_count ?? row.book_count ?? 0
      const seriesCount = row.series_book_count ?? row.book_count ?? 0
      return h('span', { class: 'progress-text' }, `${absCount}/${seriesCount}`)
    },
  })

  // Hardcover link column on tablet+
  if (!isMobile.value) {
    cols.push({
      title: 'Hardcover',
      key: 'hardcover_status',
      width: 100,
      align: 'center',
      render: (row) => h(HardcoverLinkBadge, {
        linked: !!row.hardcover_series_id,
        confidence: row.hardcover_link_confidence ?? 0,
        seriesName: row.hardcover_series_name,
        onEdit: () => emit('editLink', row),
      }),
    })
  }

  // Actions dropdown
  cols.push({
    title: '',
    key: 'actions',
    width: 60,
    align: 'center',
    render: (row) => h(SeriesActionsDropdown, {
      series: row,
      onFindMissing: (name, hcId) => emit('diff', name, hcId),
      onEditLink: (s) => emit('editLink', s),
      onRefresh: (s) => emit('refresh', s),
    }),
  })

  return cols
})

// Navigate to SeriesView for full details
function navigateToSeriesView(row) {
  router.push({
    name: 'series',
    query: {
      title: row.name,
      limit: '20',
      ...(row.hardcover_series_id && { series_id: row.hardcover_series_id }),
    },
  })
}

// Render expanded row content - shows missing books grid
function renderExpandedRow(row) {
  return h(ExpandedSeriesContent, {
    seriesName: row.name,
    hardcoverSeriesId: row.hardcover_series_id,
    absBookCount: row.abs_book_count ?? row.book_count ?? 0,
    missingCount: row.missing_count ?? 0,
    hardcoverLinkConfidence: row.hardcover_link_confidence ?? 0,
    hardcoverSeriesName: row.hardcover_series_name,
    onSearch: (book) => emit('search', book),
    onViewDetails: () => navigateToSeriesView(row),
    onEditLink: () => emit('editLink', row),
  })
}
</script>

<template>
  <NDataTable
    :columns="columns"
    :data="series"
    :row-key="row => row.id"
    :single-line="false"
    :expanded-row-keys="expandedRowKeys"
    @update:expanded-row-keys="handleExpand"
    striped
    class="series-table"
  />
</template>

<style scoped>
.series-table {
  --n-td-padding: 12px 8px;
}

.series-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.series-name {
  font-weight: 500;
  color: var(--text-primary);
}

.progress-text {
  font-family: monospace;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

/* Responsive adjustments */
@media (max-width: 767px) {
  .series-table {
    --n-td-padding: 10px 6px;
  }

  .series-name {
    font-size: 0.95rem;
  }
}
</style>
