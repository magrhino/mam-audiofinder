/**
 * useMAMSearchDataTable Composable
 * Customized table logic for MAM Audiobook Finder search functionality
 * Provides column definitions, pagination, sorting, and filtering optimized for search results
 */

import { ref, computed, h } from 'vue'
import { NButton, NTag, NTooltip, NText, NSpace } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'
import { formatSize, escapeHtml } from '@core/utils.js'
import CoverImage from '../../components/CoverImage.vue'
import AudiobookFormatIcon from '../../components/icons/AudiobookFormatIcon.vue'
import FileSizeIcon from '../../components/icons/FileSizeIcon.vue'
import SeedersIcon from '../../components/icons/SeedersIcon.vue'
import DateUploadedIcon from '../../components/icons/DateUploadedIcon.vue'

/**
 * Parse size values to bytes for accurate sorting
 * Handles both numeric bytes and string formats like "1.1 GiB", "768 MiB", or "1,132 MiB"
 * @param {number|string} size - Size value (numeric bytes or string with unit)
 * @returns {number} Size in bytes (0 for invalid input)
 */
function parseSizeToBytes(size) {
  if (size == null || size === '') return 0

  // If already numeric, return as-is
  const numericSize = Number(size)
  if (Number.isFinite(numericSize)) return numericSize

  // Strip commas from string format (e.g., "1,132 MiB" → "1132 MiB")
  const cleanedSize = String(size).replace(/,/g, '')

  // Parse string format like "1.1 GiB", "768 MiB", or "1132 MiB" (after comma removal)
  const match = cleanedSize.match(/^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)?$/i)
  if (!match) return 0

  const value = parseFloat(match[1])
  const unit = (match[2] || 'B').toUpperCase()

  // Multipliers for decimal (KB, MB, GB) and binary (KiB, MiB, GiB) units
  const multipliers = {
    'B': 1,
    'KB': 1000,
    'MB': 1000000,
    'GB': 1000000000,
    'TB': 1000000000000,
    'KIB': 1024,
    'MIB': 1048576,
    'GIB': 1073741824,
    'TIB': 1099511627776
  }

  return value * (multipliers[unit] || 1)
}

/**
 * Create column definitions based on view type
 * @param {string} viewType - 'search' | 'history' | 'showcase'
 * @param {object} callbacks - { onAdd, onVerify, onDelete, isItemLoading }
 * @param {object} responsive - { isMobile, isTablet } breakpoint flags
 * @returns {Array} Column configuration for n-data-table
 */
function createColumns(viewType, callbacks, responsive = {}) {
  const { onAdd, onVerify, onDelete, isItemLoading } = callbacks
  const { isMobile = false, isTablet = false } = responsive

  const columns = {
    // Expandable row column (mobile only) - shows hidden fields
    expand: {
      type: 'expand',
      expandable: () => true,
      renderExpand(row) {
        // Render hidden fields in expanded section
        return h('div', {
          style: 'padding: 1rem; background: rgba(42, 42, 42, 0.3); border-radius: 8px;'
        }, [
          h(NSpace, { vertical: true, size: 12 }, {
            default: () => [
              // Author
              h('div', {}, [
                h(NText, { depth: 3, strong: true }, { default: () => 'Author: ' }),
                h(NText, { depth: 2 }, { default: () => escapeHtml(row.author_info || row.author || 'N/A') })
              ]),
              // Narrator
              h('div', {}, [
                h(NText, { depth: 3, strong: true }, { default: () => 'Narrator: ' }),
                h(NText, { depth: 2 }, { default: () => escapeHtml(row.narrator_info || row.narrator || 'N/A') })
              ]),
              // Format
              h('div', {}, [
                h(NText, { depth: 3, strong: true }, { default: () => 'Format: ' }),
                h(NText, { depth: 2 }, { default: () => escapeHtml(row.format || 'N/A') })
              ]),
              // Seeders/Leechers
              h('div', {}, [
                h(NText, { depth: 3, strong: true }, { default: () => 'Seeders/Leechers: ' }),
                h(NText, { depth: 2 }, {
                  default: () => `${row.seeders ?? '-'} / ${row.leechers ?? '-'}`
                })
              ]),
              // Uploaded date
              h('div', {}, [
                h(NText, { depth: 3, strong: true }, { default: () => 'Uploaded: ' }),
                h(NText, { depth: 2 }, { default: () => escapeHtml(row.added || 'N/A') })
              ])
            ]
          })
        ])
      }
    },

    // Cover column with library indicator, tooltip, and MAM link functionality
    cover: {
      title: 'Cover',
      key: 'cover',
      width: 80,
      render(row) {
        return h(NTooltip, {}, {
          trigger: () => h(CoverImage, {
            mamId: String(row.id || ''),
            title: row.title || '',
            author: row.author_info || row.author || '',
            width: 60,
            height: 80,
            inLibrary: row.in_abs_library || false,
            onClick: row.id ? () => {
              const url = `https://www.myanonamouse.net/t/${encodeURIComponent(row.id)}`
              window.open(url, '_blank', 'noopener,noreferrer')
            } : null
          }),
          default: () => 'Link to MAM Page'
        })
      }
    },

    // Title column with escaping and responsive truncation
    title: {
      title: 'Title',
      key: 'title',
      sorter: (a, b) => (a.title || '').localeCompare(b.title || ''),
      filter(value, row) {
        return row.title && row.title.toLowerCase().includes(value.toLowerCase())
      },
      filterOptionValues: [],
      render(row) {
        return h('span', {
          class: 'responsive-title',
          title: row.title || ''  // Native tooltip for full text on hover
        }, escapeHtml(row.title || ''))
      }
    },

    // Author column with filtering
    author: {
      title: 'Author',
      key: 'author',
      minWidth: 150,
      sorter: (a, b) => {
        const authorA = a.author_info || a.author || ''
        const authorB = b.author_info || b.author || ''
        return authorA.localeCompare(authorB)
      },
      filter(value, row) {
        const author = row.author_info || row.author || ''
        return author.toLowerCase().includes(value.toLowerCase())
      },
      filterOptionValues: [],
      render(row) {
        return h('span', {}, escapeHtml(row.author_info || row.author || ''))
      }
    },

    // Narrator column with filtering (responsive width for tablet compression)
    narrator: {
      title: 'Narrator',
      key: 'narrator',
      minWidth: isTablet ? 120 : 150,  // Compressed width on tablet for 10-12" displays
      sorter: (a, b) => {
        const narratorA = a.narrator_info || a.narrator || ''
        const narratorB = b.narrator_info || b.narrator || ''
        return narratorA.localeCompare(narratorB)
      },
      filter(value, row) {
        const narrator = row.narrator_info || row.narrator || ''
        return narrator.toLowerCase().includes(value.toLowerCase())
      },
      filterOptionValues: [],
      render(row) {
        return h('span', {}, escapeHtml(row.narrator_info || row.narrator || ''))
      }
    },

    // Filetype/Format column with filtering (no sorting - uses filter dropdown)
    format: {
      title: () => h(NTooltip, {}, {
        trigger: () => h(AudiobookFormatIcon, { size: 20 }),
        default: () => 'Filetype - Filter Only'
      }),
      key: 'format',
      minWidth: 90,
      filterOptions: [
        { label: 'MP3', value: 'MP3' },
        { label: 'M4B', value: 'M4B' },
        { label: 'M4A', value: 'M4A' },
        { label: 'FLAC', value: 'FLAC' },
        { label: 'OGG', value: 'OGG' }
      ],
      filter(value, row) {
        return row.format && row.format.toUpperCase().includes(value.toUpperCase())
      },
      render(row) {
        return h('span', {}, escapeHtml(row.format || ''))
      }
    },

    // Size column
    size: {
      title: () => h(NTooltip, {}, {
        trigger: () => h(FileSizeIcon, { size: 20 }),
        default: () => 'Size - Click to Sort'
      }),
      key: 'size',
      minWidth: 100,
      align: 'right',
      sorter: (row1, row2) => {
        // Parse size values (handles both numeric bytes and string formats like "1.1 GiB")
        const size1 = parseSizeToBytes(row1.size)
        const size2 = parseSizeToBytes(row2.size)
        return size1 - size2
      },
      customNextSortOrder: (order) => {
        // Only toggle between ascend and descend (no unsorted state)
        if (order === 'ascend') return 'descend'
        return 'ascend'
      },
      render(row) {
        return h('span', {}, formatSize(row.size))
      }
    },

    // Seeders/Leechers column (search view)
    seeders: {
      title: () => h(NTooltip, {}, {
        trigger: () => h(SeedersIcon, { size: 20 }),
        default: () => 'Seeders - Click to Sort'
      }),
      key: 'seeders',
      minWidth: 110,
      align: 'right',
      defaultSortOrder: 'descend',
      sorter: (rowA, rowB) => {
        const seedersA = rowA.seeders ?? 0
        const seedersB = rowB.seeders ?? 0
        return seedersA - seedersB
      },
      render(row) {
        const s = row.seeders ?? '-'
        const l = row.leechers ?? '-'
        return h('span', {}, `${s} / ${l}`)
      }
    },

    // Uploaded/Added date column
    uploaded: {
      title: () => h(NTooltip, {}, {
        trigger: () => h(DateUploadedIcon, { size: 20 }),
        default: () => 'Date Uploaded - Click to Sort'
      }),
      key: 'added',
      minWidth: 140,
      sorter: (rowA, rowB) => {
        const dateA = new Date(rowA.added || 0)
        const dateB = new Date(rowB.added || 0)
        return dateA.getTime() - dateB.getTime()
      },
      render(row) {
        return h('span', {}, escapeHtml(row.added || ''))
      }
    },

    // Add action column (search view)
    addAction: {
      title: 'Add',
      key: 'action',
      width: isMobile ? 60 : (isTablet ? 90 : 120),
      render(row) {
        const isDisabled = !(row.dl || row.id)
        const itemLoading = isItemLoading ? isItemLoading(row.id) : false

        // Responsive button labels: Mobile: '+', Tablet: 'Add', Desktop: 'Add to qBittorrent'
        const buttonLabel = itemLoading
          ? (isMobile ? '...' : 'Adding...')
          : (isMobile ? '+' : (isTablet ? 'Add' : 'Add to qBittorrent'))

        return h(NButton, {
          size: 'small',
          type: 'primary',
          class: 'glass-button-primary',
          disabled: isDisabled || itemLoading,
          loading: itemLoading,
          onClick: () => onAdd && onAdd(row)
        }, {
          default: () => buttonLabel
        })
      }
    },

    // Status column (history view)
    status: {
      title: 'Status',
      key: 'qb_status',
      filterOptions: [
        { label: 'Downloading', value: 'downloading' },
        { label: 'Seeding', value: 'seeding' },
        { label: 'Paused', value: 'paused' },
        { label: 'Complete', value: 'complete' },
        { label: 'Error', value: 'error' }
      ],
      filter(value, row) {
        return row.qb_status && row.qb_status.toLowerCase() === value.toLowerCase()
      },
      render(row) {
        if (!row.qb_status) return null
        const typeMap = {
          downloading: 'info',
          seeding: 'success',
          paused: 'warning',
          complete: 'success',
          error: 'error'
        }
        return h(NTag, {
          type: typeMap[row.qb_status.toLowerCase()] || 'default',
          size: 'small',
          class: 'glass-tag',
          bordered: false
        }, { default: () => row.qb_status })
      }
    },

    // Verification status column (history view)
    verification: {
      title: 'Verification',
      key: 'abs_verify_status',
      filterOptions: [
        { label: '✓ Verified', value: 'verified' },
        { label: '⚠ Mismatch', value: 'mismatch' },
        { label: '✗ Not Found', value: 'not_found' },
        { label: '? Unreachable', value: 'unreachable' }
      ],
      filter(value, row) {
        return row.abs_verify_status && row.abs_verify_status === value
      },
      render(row) {
        if (!row.abs_verify_status) return null
        const iconMap = {
          verified: '✓',
          mismatch: '⚠',
          not_found: '✗',
          unreachable: '?'
        }
        const typeMap = {
          verified: 'success',
          mismatch: 'warning',
          not_found: 'error',
          unreachable: 'default'
        }
        const icon = iconMap[row.abs_verify_status] || ''
        return h(NTag, {
          type: typeMap[row.abs_verify_status] || 'default',
          size: 'small',
          class: 'glass-tag',
          bordered: false
        }, { default: () => `${icon} ${row.abs_verify_status}` })
      }
    },

    // History actions column (verify + delete)
    historyActions: {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render(row) {
        return h('div', { style: 'display: flex; gap: 8px;' }, [
          h(NButton, {
            size: 'small',
            class: 'glass-button',
            onClick: () => onVerify && onVerify(row)
          }, { default: () => '🔄 Verify' }),
          h(NButton, {
            size: 'small',
            type: 'error',
            class: 'glass-button',
            onClick: () => onDelete && onDelete(row)
          }, { default: () => '🗑 Delete' })
        ])
      }
    }
  }

  // Define column sets for each view type
  const viewColumns = {
    search: [
      columns.cover,
      columns.title,
      columns.author,
      columns.narrator,
      columns.format,
      columns.size,
      columns.seeders,
      columns.uploaded,
      columns.addAction
    ],
    history: [
      columns.cover,
      columns.title,
      columns.author,
      columns.narrator,
      columns.status,
      columns.verification,
      columns.uploaded,
      columns.historyActions
    ],
    showcase: [
      columns.format,
      columns.size,
      columns.seeders,
      columns.uploaded,
      columns.addAction
    ]
  }

  return viewColumns[viewType] || viewColumns.search
}

/**
 * Main composable for MAM search data table functionality
 * @param {object} config - Configuration object
 * @param {string} config.viewType - Type of view ('search' | 'history' | 'showcase')
 * @param {function} config.onAdd - Callback for Add button
 * @param {function} config.onVerify - Callback for Verify button (history only)
 * @param {function} config.onDelete - Callback for Delete button (history only)
 * @param {function} config.isItemLoading - Function to check if item is loading (optional)
 * @param {number} config.defaultPageSize - Default pagination size (default: 25)
 * @returns {object} Table state and methods
 */
export function useMAMSearchDataTable(config = {}) {
  const {
    viewType = 'search',
    onAdd = null,
    onVerify = null,
    onDelete = null,
    isItemLoading = null,
    defaultPageSize = 25
  } = config

  // Responsive breakpoints using @vueuse/core
  const breakpoints = useBreakpoints({
    mobile: 0,      // 0-767px
    tablet: 768,    // 768-1023px
    desktop: 1024   // 1024px+
  })

  const isMobile = computed(() => breakpoints.smaller('tablet').value)
  const isTablet = computed(() => breakpoints.between('tablet', 'desktop').value)

  // Responsive scroll-x for table horizontal scrolling
  const scrollX = computed(() => {
    if (breakpoints.greater('desktop').value) {
      return 1400 // Desktop: More space for expanded columns
    } else if (breakpoints.greater('tablet').value) {
      return 1200 // Tablet: Standard layout
    } else {
      return 900 // Mobile: Compact layout
    }
  })

  // Table ref for programmatic control
  const tableRef = ref(null)

  // Data and state
  const data = ref([])
  const loading = ref(false)

  // Pagination configuration
  const pagination = ref({
    pageSize: defaultPageSize,
    pageSizes: [25, 50, 100],
    showSizePicker: false,  // Disabled - use search form dropdown instead
    showQuickJumper: true
  })

  // Column definitions with responsive filtering
  const columns = computed(() => {
    const allColumns = createColumns(
      viewType,
      { onAdd, onVerify, onDelete, isItemLoading },
      { isMobile: isMobile.value, isTablet: isTablet.value }
    )

    // Filter columns based on screen size
    if (viewType === 'search') {
      // Mobile: Show expand column + essential columns (expand, cover, title, size, actions)
      if (isMobile.value) {
        const essentialColumns = allColumns.filter(col =>
          ['cover', 'title', 'size', 'action'].includes(col.key)
        )
        // Add expand column at the beginning
        const expandColumn = allColumns.find(col => col.type === 'expand')
        return expandColumn ? [expandColumn, ...essentialColumns] : essentialColumns
      }

      // Tablet: Hide less critical columns (format, uploaded) and no expand column
      if (isTablet.value) {
        return allColumns.filter(col =>
          col.type !== 'expand' && !['format', 'uploaded'].includes(col.key)
        )
      }
    }

    // Desktop or other views: Show all columns except expand (expand is mobile-only)
    return allColumns.filter(col => col.type !== 'expand')
  })

  // Programmatic table controls
  const sort = (key, order) => {
    if (tableRef.value) {
      tableRef.value.sort(key, order)
    }
  }

  const clearSorter = () => {
    if (tableRef.value) {
      tableRef.value.clearSorter()
    }
  }

  const filter = (filters) => {
    if (tableRef.value) {
      tableRef.value.filter(filters)
    }
  }

  const clearFilters = () => {
    if (tableRef.value) {
      tableRef.value.clearFilters()
    }
  }

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
    scrollX,

    // Responsive breakpoint helpers
    isMobile,
    isTablet,

    // Methods
    setData,
    clearData,
    sort,
    clearSorter,
    filter,
    clearFilters
  }
}
