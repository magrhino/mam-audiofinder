/**
 * useSeriesDataTable Composable
 * Table configuration for Hardcover series search results
 * Provides column definitions, pagination, and sorting optimized for series discovery
 */

import { ref, computed, h } from 'vue'
import { NButton, NTooltip } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'
import { escapeHtml } from '@core/utils.js'

/**
 * Create column definitions for series results table
 * @param {Function} onSelect - Callback for View button click
 * @param {Object} responsive - { isMobile, isTablet } breakpoint flags
 * @returns {Array} Column configuration for n-data-table
 */
function createSeriesColumns(onSelect, responsive = {}) {
  const { isMobile = false, isTablet = false } = responsive

  return [
    {
      title: 'Series',
      key: 'series_name',
      minWidth: 250,
      sorter: (a, b) => (a.series_name || '').localeCompare(b.series_name || ''),
      render(row) {
        return h('span', {
          class: 'responsive-title',
          title: row.series_name || ''  // Native tooltip for full text on hover
        }, escapeHtml(row.series_name || ''))
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
      width: isMobile ? 80 : 100,
      align: 'center',
      render(row) {
        // Responsive button labels: Mobile: 'View', Tablet/Desktop: 'View'
        // (All sizes use 'View' for series - simple action)
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
 * @param {Object} responsive - { isMobile, isTablet } breakpoint flags
 * @returns {Array} Column configuration for n-data-table
 */
function createBooksColumns(responsive = {}) {
  const { isMobile = false, isTablet = false } = responsive

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

  // Responsive breakpoints using @vueuse/core
  const breakpoints = useBreakpoints({
    mobile: 0,      // 0-767px
    tablet: 768,    // 768-1023px
    desktop: 1024   // 1024px+
  })

  const isMobile = computed(() => breakpoints.smaller('tablet').value)
  const isTablet = computed(() => breakpoints.between('tablet', 'desktop').value)

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

  // Column definitions with responsive filtering
  const columns = computed(() => {
    const allColumns = createSeriesColumns(
      onSelect,
      { isMobile: isMobile.value, isTablet: isTablet.value }
    )

    // Filter columns based on screen size
    // Mobile: Show only series name and action
    if (isMobile.value) {
      return allColumns.filter(col =>
        ['series_name', 'action'].includes(col.key)
      )
    }

    // Tablet: Hide book_count and readers_count
    if (isTablet.value) {
      return allColumns.filter(col =>
        !['book_count', 'readers_count'].includes(col.key)
      )
    }

    // Desktop: Show all columns
    return allColumns
  })

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

  // Responsive breakpoints using @vueuse/core
  const breakpoints = useBreakpoints({
    mobile: 0,      // 0-767px
    tablet: 768,    // 768-1023px
    desktop: 1024   // 1024px+
  })

  const isMobile = computed(() => breakpoints.smaller('tablet').value)
  const isTablet = computed(() => breakpoints.between('tablet', 'desktop').value)

  const tableRef = ref(null)
  const data = ref([])

  const pagination = ref({
    pageSize: defaultPageSize,
    showQuickJumper: true
  })

  // Column definitions with responsive filtering
  const columns = computed(() => {
    const allColumns = createBooksColumns({
      isMobile: isMobile.value,
      isTablet: isTablet.value
    })

    // Filter columns based on screen size
    // Mobile: Show only title
    if (isMobile.value) {
      return allColumns.filter(col => col.key === 'title')
    }

    // Tablet: Hide release_year
    if (isTablet.value) {
      return allColumns.filter(col => col.key !== 'release_year')
    }

    // Desktop: Show all columns
    return allColumns
  })

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
