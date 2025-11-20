/**
 * useSeriesDataTable Composable
 * Table configuration for Hardcover series search results
 * Provides column definitions, pagination, and sorting optimized for series discovery
 */

import { ref, computed, h } from 'vue'
import { NButton, NTooltip } from 'naive-ui'
import { escapeHtml } from '@core/utils.js'

/**
 * Create column definitions for series results table
 * @param {Function} onSelect - Callback for View button click
 * @returns {Array} Column configuration for n-data-table
 */
function createSeriesColumns(onSelect) {
  return [
    {
      title: 'Series',
      key: 'series_name',
      minWidth: 250,
      sorter: (a, b) => (a.series_name || '').localeCompare(b.series_name || ''),
      render(row) {
        return h('span', {}, escapeHtml(row.series_name || ''))
      }
    },
    {
      title: 'Author',
      key: 'author_name',
      minWidth: 180,
      sorter: (a, b) => (a.author_name || '').localeCompare(b.author_name || ''),
      render(row) {
        return h('span', {}, escapeHtml(row.author_name || ''))
      }
    },
    {
      title: () => h(NTooltip, {}, {
        trigger: () => h('span', {}, '📚'),
        default: () => 'Number of Books in Series'
      }),
      key: 'book_count',
      width: 100,
      align: 'center',
      sorter: (a, b) => (a.book_count || 0) - (b.book_count || 0),
      render(row) {
        return h('span', {}, row.book_count || 0)
      }
    },
    {
      title: () => h(NTooltip, {}, {
        trigger: () => h('span', {}, '📖'),
        default: () => 'Total Readers on Hardcover'
      }),
      key: 'readers_count',
      width: 120,
      align: 'center',
      sorter: (a, b) => (a.readers_count || 0) - (b.readers_count || 0),
      render(row) {
        const count = row.readers_count || 0
        return h('span', {}, count.toLocaleString())
      }
    },
    {
      title: 'Action',
      key: 'action',
      width: 100,
      align: 'center',
      render(row) {
        return h(NButton, {
          size: 'small',
          type: 'primary',
          onClick: () => onSelect && onSelect(row)
        }, { default: () => 'View' })
      }
    }
  ]
}

/**
 * Create column definitions for books within a series
 * @returns {Array} Column configuration for n-data-table
 */
function createBooksColumns() {
  return [
    {
      title: 'Title',
      key: 'title',
      minWidth: 250,
      sorter: (a, b) => (a.title || '').localeCompare(b.title || ''),
      render(row) {
        return h('span', {}, escapeHtml(row.title || ''))
      }
    },
    {
      title: 'Author',
      key: 'author',
      minWidth: 180,
      sorter: (a, b) => {
        const authorA = a.author || a.author_name || ''
        const authorB = b.author || b.author_name || ''
        return authorA.localeCompare(authorB)
      },
      render(row) {
        return h('span', {}, escapeHtml(row.author || row.author_name || ''))
      }
    },
    {
      title: 'Year',
      key: 'release_year',
      width: 100,
      align: 'center',
      sorter: (a, b) => (a.release_year || 0) - (b.release_year || 0),
      render(row) {
        return h('span', {}, row.release_year || '—')
      }
    }
  ]
}

/**
 * Main composable for series data table functionality
 * @param {Object} config - Configuration object
 * @param {Function} config.onSelect - Callback for View button
 * @param {number} config.defaultPageSize - Default pagination size (default: 20)
 * @returns {Object} Table state and methods
 */
export function useSeriesDataTable(config = {}) {
  const {
    onSelect = null,
    defaultPageSize = 20
  } = config

  // Table ref for programmatic control
  const tableRef = ref(null)

  // Data and state
  const data = ref([])
  const loading = ref(false)

  // Pagination configuration
  const pagination = ref({
    pageSize: defaultPageSize,
    pageSizes: [10, 20, 30, 50],
    showSizePicker: false,  // Disabled - use form dropdown instead
    showQuickJumper: true
  })

  // Column definitions
  const columns = computed(() => createSeriesColumns(onSelect))

  // Set table data
  const setData = (newData) => {
    data.value = newData || []
  }

  // Clear table data
  const clearData = () => {
    data.value = []
  }

  return {
    // Refs
    tableRef,
    data,
    loading,
    pagination,
    columns,

    // Methods
    setData,
    clearData
  }
}

/**
 * Composable for books within a series table
 * @param {Object} config - Configuration object
 * @param {number} config.defaultPageSize - Default pagination size (default: 10)
 * @returns {Object} Table state and methods
 */
export function useBooksDataTable(config = {}) {
  const {
    defaultPageSize = 10
  } = config

  const tableRef = ref(null)
  const data = ref([])

  const pagination = ref({
    pageSize: defaultPageSize,
    showQuickJumper: true
  })

  const columns = computed(() => createBooksColumns())

  const setData = (newData) => {
    data.value = newData || []
  }

  const clearData = () => {
    data.value = []
  }

  return {
    tableRef,
    data,
    pagination,
    columns,
    setData,
    clearData
  }
}
