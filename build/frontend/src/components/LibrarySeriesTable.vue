<script setup>
import { h, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NDataTable, NTag, NImage, NButton, NScrollbar } from 'naive-ui'
import SeriesCompletionRing from '@/components/SeriesCompletionRing.vue'
import HardcoverLinkBadge from '@/components/HardcoverLinkBadge.vue'
import MissingBooksPopover from '@/components/MissingBooksPopover.vue'
import SeriesActionsDropdown from '@/components/SeriesActionsDropdown.vue'
import { useBreakpoints } from '@/composables/useBreakpoints'

const props = defineProps({
  series: { type: Array, required: true },
})

const emit = defineEmits(['diff', 'editLink', 'refresh', 'addToWishlist'])
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

// Render expanded row content - shows book grid
function renderExpandedRow(row) {
  // This will show a grid of books when we have the data
  // For now, show a placeholder that indicates loading/empty state
  return h('div', { class: 'expanded-row' }, [
    h('div', { class: 'expanded-header' }, [
      h('span', { class: 'expanded-title' }, `Books in ${row.name}`),
      h(NButton, {
        size: 'tiny',
        type: 'primary',
        onClick: () => {
          router.push({
            name: 'series',
            query: {
              title: row.name,
              limit: '20',
              ...(row.hardcover_series_id && { series_id: row.hardcover_series_id }),
            },
          })
        },
      }, () => 'View Full Details'),
    ]),
    h('div', { class: 'expanded-content' }, [
      h('p', { class: 'expanded-hint' }, [
        `${row.abs_book_count ?? 0} books in your library`,
        row.missing_count > 0
          ? ` • ${row.missing_count} missing from Hardcover series`
          : ' • Series complete!',
      ]),
      // Mobile-only: show link status
      isMobile.value && row.hardcover_series_id
        ? h('div', { class: 'mobile-link-status' }, [
            h(HardcoverLinkBadge, {
              linked: true,
              confidence: row.hardcover_link_confidence ?? 0,
              seriesName: row.hardcover_series_name,
              onEdit: () => emit('editLink', row),
            }),
          ])
        : null,
    ]),
  ])
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

/* Expanded row styles */
.expanded-row {
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  margin: 8px 0;
}

.expanded-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.expanded-title {
  font-weight: 600;
  color: var(--text-primary);
}

.expanded-content {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.expanded-hint {
  margin: 0;
}

.mobile-link-status {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-link-status::before {
  content: 'Hardcover:';
  font-size: 0.85rem;
  color: var(--text-subtle);
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
