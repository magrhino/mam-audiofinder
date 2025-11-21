/**
 * useHistoryDataTable Composable
 * Table configuration for History view with responsive columns and expansion support
 * Uses n-data-table's built-in expansion mechanism
 */

import { ref, computed, h } from 'vue'
import { useBreakpoints } from '@vueuse/core'
import { NButton, NPopconfirm, NTooltip, NSpace } from 'naive-ui'
import CoverImage from '../../components/CoverImage.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import HistoryImportForm from '../../components/HistoryImportForm.vue'

/**
 * Create column definitions for history table
 * @param {object} config - Configuration object
 * @param {function} config.onVerify - Callback for verify button
 * @param {function} config.onRemove - Callback for remove button
 * @param {boolean} config.isMobile - Mobile breakpoint flag
 * @param {string} config.absBaseUrl - ABS base URL for library links
 * @returns {Array} Column configuration for n-data-table
 */
function createColumns(config) {
  const { onVerify, onRemove, isMobile, absBaseUrl } = config

  const columns = [
    // Expand column - built-in n-data-table expansion
    {
      type: 'expand',
      expandable: () => true,
      renderExpand: (row) => {
        return h('div', { style: 'padding: 1rem;' }, [
          h(HistoryImportForm, {
            item: row,
            onUpdated: () => {
              // Trigger parent update via row metadata
              if (row._onUpdated) row._onUpdated()
            },
            onClose: () => {
              // Collapse is handled by n-data-table automatically
            }
          })
        ])
      }
    },

    // Cover column
    {
      title: 'Cover',
      key: 'cover',
      width: 80,
      render(row) {
        return h(CoverImage, {
          mamId: String(row.mam_id || ''),
          title: row.title || '',
          author: row.author || '',
          width: 60,
          height: 90,
          inLibrary: false
        })
      }
    },

    // Title column
    {
      title: 'Title',
      key: 'title',
      minWidth: 150,
      render(row) {
        return h('span', {}, row.title || '')
      }
    },

    // Author column (hidden on mobile)
    {
      title: 'Author',
      key: 'author',
      minWidth: 120,
      render(row) {
        return h('span', {}, row.author || '')
      }
    },

    // Narrator column (hidden on mobile)
    {
      title: 'Narrator',
      key: 'narrator',
      minWidth: 120,
      render(row) {
        return h('span', {}, row.narrator || '')
      }
    },

    // Link column
    {
      title: 'Link',
      key: 'link',
      width: 60,
      align: 'center',
      render(row) {
        if (!row.mam_id) return null
        const url = `https://www.myanonamouse.net/t/${encodeURIComponent(row.mam_id)}`
        return h('a', {
          href: url,
          target: '_blank',
          rel: 'noopener noreferrer',
          title: 'Open on MAM'
        }, '🔗')
      }
    },

    // When column
    {
      title: 'When',
      key: 'added_at',
      minWidth: 140,
      render(row) {
        if (!row.added_at) return ''
        return new Date(row.added_at.replace(' ', 'T') + 'Z').toLocaleString()
      }
    },

    // Status column
    {
      title: 'Status',
      key: 'status',
      minWidth: 140,
      render(row) {
        const statusVariantMap = {
          grey: 'muted',
          blue: 'info',
          yellow: 'warning',
          green: 'success',
          red: 'danger'
        }
        const statusVariant = statusVariantMap[row.qb_status_color || 'grey'] || 'muted'

        const verifyBadgeConfig = (() => {
          if (!row.imported_at || !row.abs_verify_status) return null
          const note = row.abs_verify_note || ''
          if (row.abs_verify_status === 'verified') {
            return { label: 'Verified', variant: 'success', title: note }
          }
          if (row.abs_verify_status === 'mismatch') {
            return { label: 'Mismatch', variant: 'warning', title: note }
          }
          if (row.abs_verify_status === 'not_found') {
            return { label: 'Missing', variant: 'danger', title: note }
          }
          return { label: row.abs_verify_status, variant: 'muted', title: note }
        })()

        const badges = [
          h(StatusBadge, {
            label: row.qb_status,
            variant: statusVariant,
            title: row.path_warning || ''
          })
        ]

        // Add path warning icon
        if (row.path_warning) {
          badges.push(
            h('span', {
              title: row.path_warning,
              style: 'color: #e74c3c; cursor: help; margin-left: 4px; font-size: 1.1em;'
            }, '⚠️')
          )
        }

        // Add verification badge
        if (verifyBadgeConfig) {
          badges.push(
            h(StatusBadge, {
              label: verifyBadgeConfig.label,
              variant: verifyBadgeConfig.variant,
              title: verifyBadgeConfig.title
            })
          )
        }

        return h('div', { style: 'display: flex; gap: 4px; align-items: center; flex-wrap: wrap;' }, badges)
      }
    },

    // Actions column (Verify + Remove) with icon header
    {
      title: () => h(NTooltip, {}, {
        trigger: () => h('span', { style: 'font-size: 1.2em; cursor: help;' }, '⚙️'),
        default: () => 'Actions'
      }),
      key: 'actions',
      width: isMobile ? 120 : 200,
      render(row) {
        const libraryItemUrl = (row.abs_verify_status === 'mismatch' && row.abs_item_id && absBaseUrl)
          ? `${absBaseUrl}/item/${row.abs_item_id}`
          : null

        const buttons = [
          // Verify button
          h(NButton, {
            type: 'info',
            ghost: true,
            round: true,
            size: 'small',
            disabled: !row.imported_at,
            onClick: () => onVerify && onVerify(row)
          }, {
            default: () => isMobile ? '🔄' : '🔄 Verify'
          }),

          // Remove button with confirmation
          h(NPopconfirm, {
            positiveText: 'Yes, remove',
            negativeText: 'Cancel',
            onPositiveClick: () => onRemove && onRemove(row.id)
          }, {
            trigger: () => h(NButton, {
              type: 'error',
              ghost: true,
              round: true,
              size: 'small'
            }, {
              default: () => isMobile ? '🗑️' : '🗑️ Remove'
            }),
            default: () => 'Remove this history item?'
          })
        ]

        // Add library link if applicable (desktop only)
        if (libraryItemUrl && !isMobile) {
          buttons.splice(1, 0,
            h(NButton, {
              tag: 'a',
              href: libraryItemUrl,
              target: '_blank',
              type: 'warning',
              ghost: true,
              round: true,
              size: 'tiny'
            }, {
              default: () => '📚 Library'
            })
          )
        }

        return h(NSpace, { size: 4 }, { default: () => buttons })
      }
    }
  ]

  return columns
}

/**
 * Main composable for history data table
 * @param {object} config - Configuration object
 * @param {function} config.onUpdated - Callback when data needs refresh
 * @returns {object} Table state and methods
 */
export function useHistoryDataTable(config = {}) {
  const { onUpdated } = config

  // Responsive breakpoints
  const breakpoints = useBreakpoints({
    mobile: 0,
    tablet: 768,
    desktop: 1024
  })

  const isMobile = computed(() => breakpoints.smaller('tablet').value)

  // Table refs and state
  const tableRef = ref(null)
  const absBaseUrl = ref('')

  /**
   * Verify handler
   * @param {object} row - Row data
   */
  const handleVerify = async (row) => {
    // Import API in the handler to avoid circular dependencies
    const { useApi } = await import('../useApi')
    const api = useApi()

    try {
      const result = await api.verifyHistoryItem(row.id)
      if (result.ok) {
        onUpdated && onUpdated()
      }
    } catch (err) {
      console.error('[useHistoryDataTable] Verify failed:', err)
    }
  }

  /**
   * Remove handler
   * @param {number} rowId - Row ID to remove
   */
  const handleRemove = async (rowId) => {
    // Import API in the handler to avoid circular dependencies
    const { useApi } = await import('../useApi')
    const api = useApi()

    try {
      await api.deleteHistoryItem(rowId)
      onUpdated && onUpdated()
    } catch (err) {
      console.error('[useHistoryDataTable] Remove failed:', err)
    }
  }

  // Column definitions with responsive behavior
  const columns = computed(() => {
    const cols = createColumns({
      onVerify: handleVerify,
      onRemove: handleRemove,
      isMobile: isMobile.value,
      absBaseUrl: absBaseUrl.value
    })

    // Filter out Author and Narrator columns on mobile
    if (isMobile.value) {
      return cols.filter(col => !['author', 'narrator'].includes(col.key))
    }

    return cols
  })

  /**
   * Enrich data with update callback
   * @param {Array} data - Raw history data
   * @returns {Array} Enriched data
   */
  const enrichData = (data) => {
    return data.map(row => ({
      ...row,
      _onUpdated: onUpdated
    }))
  }

  /**
   * Set ABS base URL for library links
   * @param {string} url - ABS base URL
   */
  const setAbsBaseUrl = (url) => {
    absBaseUrl.value = url || ''
  }

  return {
    tableRef,
    columns,
    isMobile,
    enrichData,
    setAbsBaseUrl
  }
}
