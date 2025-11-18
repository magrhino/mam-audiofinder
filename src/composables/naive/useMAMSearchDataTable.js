/**
 * useMAMSearchDataTable Composable
 * Customized table logic for MAM Audiobook Finder search functionality
 * Provides column definitions, pagination, sorting, and filtering optimized for search results
 */

import { ref, computed, h } from 'vue'
import { NButton, NTag, NTooltip } from 'naive-ui'
import { formatSize, escapeHtml } from '../../../app/static/js/core/utils.js'
import CoverImage from '../../components/CoverImage.vue'
import AudiobookFormatIcon from '../../components/icons/AudiobookFormatIcon.vue'
import FileSizeIcon from '../../components/icons/FileSizeIcon.vue'
import SeedersIcon from '../../components/icons/SeedersIcon.vue'
import DateUploadedIcon from '../../components/icons/DateUploadedIcon.vue'

/**
 * Create column definitions based on view type
 * @param {string} viewType - 'search' | 'history' | 'showcase'
 * @param {object} callbacks - { onAdd, onVerify, onDelete }
 * @returns {Array} Column configuration for n-data-table
 */
function createColumns(viewType, callbacks) {
  const { onAdd, onVerify, onDelete } = callbacks

  const columns = {
    // Cover column with library indicator using NaiveUI n-image with lazy loading
    cover: {
      title: 'Cover',
      key: 'cover',
      width: 80,
      render(row) {
        return h(CoverImage, {
          mamId: String(row.id || ''),
          title: row.title || '',
          author: row.author_info || row.author || '',
          width: 60,
          height: 80,
          inLibrary: row.in_abs_library || false
        })
      }
    },

    // Title column with escaping
    title: {
      title: 'Title',
      key: 'title',
      sorter: (a, b) => (a.title || '').localeCompare(b.title || ''),
      filter(value, row) {
        return row.title && row.title.toLowerCase().includes(value.toLowerCase())
      },
      filterOptionValues: [],
      render(row) {
        return h('span', {}, escapeHtml(row.title || ''))
      }
    },

    // Author column with filtering
    author: {
      title: 'Author',
      key: 'author',
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

    // Narrator column with filtering
    narrator: {
      title: 'Narrator',
      key: 'narrator',
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

    // Filetype/Format column with filtering
    format: {
      title: () => h(NTooltip, {}, {
        trigger: () => h(AudiobookFormatIcon, { size: 20 }),
        default: () => 'Filetype - Click to Sort'
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
      sorter: (a, b) => (a.size || 0) - (b.size || 0),
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
      sorter: (a, b) => (a.seeders || 0) - (b.seeders || 0),
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
      sorter: (a, b) => {
        const dateA = new Date(a.added || 0)
        const dateB = new Date(b.added || 0)
        return dateA - dateB
      },
      render(row) {
        return h('span', {}, escapeHtml(row.added || ''))
      }
    },

    // MAM link column
    link: {
      title: 'Link',
      key: 'link',
      align: 'center',
      width: 60,
      render(row) {
        if (!row.id) return null
        const url = `https://www.myanonamouse.net/t/${encodeURIComponent(row.id)}`
        return h('a', {
          href: url,
          target: '_blank',
          rel: 'noopener noreferrer',
          title: 'Open on MAM'
        }, '🔗')
      }
    },

    // Add action column (search view)
    addAction: {
      title: 'Add',
      key: 'action',
      width: 100,
      render(row) {
        const isDisabled = !(row.dl || row.id)
        return h(NButton, {
          size: 'small',
          type: 'primary',
          disabled: isDisabled,
          onClick: () => onAdd && onAdd(row)
        }, { default: () => 'Add' })
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
          size: 'small'
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
          size: 'small'
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
            onClick: () => onVerify && onVerify(row)
          }, { default: () => '🔄 Verify' }),
          h(NButton, {
            size: 'small',
            type: 'error',
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
      columns.link,
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
 * @param {number} config.defaultPageSize - Default pagination size (default: 25)
 * @returns {object} Table state and methods
 */
export function useMAMSearchDataTable(config = {}) {
  const {
    viewType = 'search',
    onAdd = null,
    onVerify = null,
    onDelete = null,
    defaultPageSize = 25
  } = config

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

  // Column definitions
  const columns = computed(() => {
    return createColumns(
      viewType,
      { onAdd, onVerify, onDelete }
    )
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

    // Methods
    setData,
    clearData,
    sort,
    clearSorter,
    filter,
    clearFilters
  }
}
