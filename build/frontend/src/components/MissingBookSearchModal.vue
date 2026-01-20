<script setup>
import { ref, watch, computed } from 'vue'
import { NModal, NButton, NSpin, NEmpty, NScrollbar, NDataTable, NTag } from 'naive-ui'
import { useApi } from '@/composables/useApi'
import { useBreakpoints } from '@/composables/useBreakpoints'
import { useAddTorrentFlow } from '@/composables/useAddTorrentFlow'
import ShowcaseCard from '@/components/ShowcaseCard.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  book: {
    type: Object,
    default: null,
  },
  seriesName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:show', 'added'])

// API and responsive
const api = useApi()
const { isMobile } = useBreakpoints()
const { addTorrent, isItemLoading } = useAddTorrentFlow()

// Search state
const searchResults = ref([])
const loading = ref(false)
const error = ref(null)

// Selected group for versions view
const selectedGroup = ref(null)

// Track added items for success feedback
const addedItems = ref([])

// Extract book title
const bookTitle = computed(() => {
  return props.book?.hardcover?.title || props.book?.title || ''
})

// Modal style
const modalStyle = computed(() => {
  if (isMobile.value) {
    return {
      width: '95vw',
      maxHeight: '90vh',
    }
  }
  return {
    width: '900px',
    maxWidth: '95vw',
    maxHeight: '85vh',
  }
})

// Versions table columns
const versionsColumns = computed(() => [
  {
    title: '',
    key: 'link',
    width: 36,
    align: 'center',
    render: (row) => {
      if (!row.id) return null
      return h(
        'a',
        {
          href: `https://www.myanonamouse.net/t/${encodeURIComponent(row.id)}`,
          target: '_blank',
          rel: 'noopener noreferrer',
          class: 'mam-link',
          title: 'View on MAM',
          onClick: (e) => e.stopPropagation(),
        },
        h(
          'svg',
          {
            width: 14,
            height: 14,
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            'stroke-width': 2,
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
          },
          [
            h('path', { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' }),
            h('polyline', { points: '15 3 21 3 21 9' }),
            h('line', { x1: 10, y1: 14, x2: 21, y2: 3 }),
          ]
        )
      )
    },
  },
  {
    title: 'Format',
    key: 'format',
    width: 70,
    render: (row) => {
      // Format is stored directly in row.format as a string like "MP3" or "M4B"
      return row.format || 'N/A'
    },
  },
  {
    title: 'Size',
    key: 'size',
    width: 90,
    render: (row) => row.size || 'N/A',
  },
  {
    title: 'S/L',
    key: 'seeders',
    width: 60,
    align: 'center',
    render: (row) => {
      const seeders = row.seeders ?? 0
      const leechers = row.leechers ?? 0
      return `${seeders}/${leechers}`
    },
  },
  {
    title: '',
    key: 'action',
    width: 90,
    align: 'center',
    render: (row) => {
      const itemId = String(row.id || '')
      const isLoading = isItemLoading(itemId)
      const isAdded = addedItems.value.includes(row.title)

      if (isAdded) {
        return h(NTag, { type: 'success', size: 'small' }, () => '✓ Added')
      }

      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          loading: isLoading,
          onClick: () => handleAddTorrent(row),
        },
        () => '+ Add'
      )
    },
  },
])

// Import h for render functions
import { h } from 'vue'

// Initialize search when modal opens with a book
watch(
  () => props.show,
  async (visible) => {
    if (visible && props.book) {
      await performSearch(bookTitle.value)
    } else if (!visible) {
      resetState()
    }
  }
)

async function performSearch(query) {
  if (!query.trim()) return

  loading.value = true
  error.value = null
  selectedGroup.value = null

  try {
    const data = await api.getShowcase({ query: query.trim(), limit: 50 })
    searchResults.value = data.groups || []
  } catch (err) {
    error.value = err.message
    searchResults.value = []
  } finally {
    loading.value = false
  }
}

function selectGroup(group) {
  selectedGroup.value = group
}

function deselectGroup() {
  selectedGroup.value = null
}

async function handleAddTorrent(rowState) {
  const result = await addTorrent(rowState, false) // false = no confirmation dialog
  if (result.success) {
    addedItems.value.push(rowState.title)
    emit('added', { title: rowState.title, ...rowState })
  }
}

function resetState() {
  searchResults.value = []
  selectedGroup.value = null
  loading.value = false
  error.value = null
  addedItems.value = []
}

function close() {
  emit('update:show', false)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :style="modalStyle"
    :closable="true"
    :mask-closable="true"
    @update:show="(val) => emit('update:show', val)"
    class="search-modal"
  >
    <template #header>
      <div class="modal-header">
        <div class="header-title">
          <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
          </svg>
          <span>Find: "{{ bookTitle }}"</span>
        </div>
        <div v-if="seriesName" class="header-series">
          {{ seriesName }}
        </div>
      </div>
    </template>

    <div class="modal-content">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <NSpin size="large" />
        <span class="loading-text">Searching MAM for audiobooks...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12" stroke-linecap="round"/>
            <line x1="12" y1="16" x2="12.01" y2="16" stroke-linecap="round"/>
          </svg>
        </div>
        <span class="error-text">{{ error }}</span>
        <NButton size="small" @click="performSearch(bookTitle)">Retry</NButton>
      </div>

      <!-- Empty state -->
      <div v-else-if="searchResults.length === 0 && !loading" class="empty-state">
        <NEmpty description="No audiobooks found on MAM">
          <template #extra>
            <span class="empty-hint">Try searching with a different title</span>
          </template>
        </NEmpty>
      </div>

      <!-- Results -->
      <template v-else>
        <!-- Back button when viewing versions -->
        <div v-if="selectedGroup" class="versions-header">
          <NButton quaternary size="small" @click="deselectGroup">
            <template #icon>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5" stroke-linecap="round"/>
                <path d="M12 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </template>
            Back to results
          </NButton>
          <span class="versions-title">{{ selectedGroup.display_title }}</span>
          <span class="versions-count">{{ selectedGroup.versions?.length || 0 }} version(s)</span>
        </div>

        <!-- Versions table -->
        <div v-if="selectedGroup" class="versions-section">
          <NScrollbar style="max-height: 300px;">
            <NDataTable
              :columns="versionsColumns"
              :data="selectedGroup.versions || []"
              :row-key="row => row.id"
              size="small"
              :bordered="false"
            />
          </NScrollbar>
        </div>

        <!-- Results grid (when no group selected) -->
        <NScrollbar v-else style="max-height: 450px;">
          <div class="results-grid" :class="{ 'mobile-grid': isMobile }">
            <ShowcaseCard
              v-for="group in searchResults"
              :key="group.mam_id"
              :group="group"
              @select="selectGroup"
            />
          </div>
        </NScrollbar>
      </template>

      <!-- Success banner -->
      <div v-if="addedItems.length > 0" class="success-banner">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke-linecap="round"/>
          <polyline points="22 4 12 14.01 9 11.01" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>Added {{ addedItems.length }} audiobook{{ addedItems.length > 1 ? 's' : '' }} to qBittorrent</span>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <NButton @click="close">Close</NButton>
      </div>
    </template>
  </NModal>
</template>

<style scoped>
/* ========================================
   Modal Container - Glass Panel Aesthetic
   ======================================== */
.search-modal {
  --modal-bg: rgba(18, 18, 18, 0.97);
  --glass-border: rgba(255, 255, 255, 0.06);
  --maroon-glow: rgba(80, 0, 0, 0.15);
  --gold-accent: rgba(220, 170, 80, 0.85);
  --success-color: rgba(80, 180, 100, 0.95);
}

.search-modal :deep(.n-card) {
  background: var(--modal-bg) !important;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--glass-border) !important;
  box-shadow:
    0 32px 64px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(80, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.search-modal :deep(.n-card-header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 16px;
}

/* ========================================
   Modal Header
   ======================================== */
.modal-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  font-size: 1.15rem;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: 0.01em;
}

.search-icon {
  color: var(--gold-accent);
  flex-shrink: 0;
  animation: icon-pulse 2s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { opacity: 0.8; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.05); }
}

.header-series {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: rgba(184, 184, 184, 0.65);
  margin-left: 32px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  width: fit-content;
}

.header-series::before {
  content: '';
  width: 4px;
  height: 4px;
  background: var(--gold-accent);
  border-radius: 50%;
  opacity: 0.6;
}

/* ========================================
   Modal Content
   ======================================== */
.modal-content {
  min-height: 240px;
  position: relative;
}

/* Inner gradient overlay for depth */
.modal-content::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at top center,
    rgba(80, 0, 0, 0.04) 0%,
    transparent 60%
  );
  pointer-events: none;
  z-index: 0;
}

/* ========================================
   Loading State
   ======================================== */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 60px 40px;
  position: relative;
  z-index: 1;
}

.loading-state :deep(.n-spin) {
  --n-color: rgba(220, 170, 80, 0.8) !important;
}

.loading-text {
  color: rgba(184, 184, 184, 0.75);
  font-size: 0.88rem;
  letter-spacing: 0.02em;
  animation: text-fade 1.5s ease-in-out infinite;
}

@keyframes text-fade {
  0%, 100% { opacity: 0.75; }
  50% { opacity: 0.5; }
}

/* ========================================
   Error State
   ======================================== */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 50px 40px;
  position: relative;
  z-index: 1;
}

.error-icon {
  color: rgba(200, 80, 80, 0.85);
  animation: error-shake 0.5s ease-in-out;
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}

.error-text {
  color: rgba(200, 80, 80, 0.9);
  font-size: 0.9rem;
  text-align: center;
  max-width: 300px;
}

/* ========================================
   Empty State
   ======================================== */
.empty-state {
  padding: 50px 40px;
  position: relative;
  z-index: 1;
}

.empty-state :deep(.n-empty) {
  --n-text-color: rgba(184, 184, 184, 0.6) !important;
}

.empty-hint {
  color: rgba(184, 184, 184, 0.5);
  font-size: 0.82rem;
  margin-top: 8px;
}

/* ========================================
   Results Grid
   ======================================== */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(165px, 1fr));
  gap: 18px;
  padding: 12px 4px;
  position: relative;
  z-index: 1;
}

.results-grid.mobile-grid {
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 14px;
}

/* Staggered card entrance animation */
.results-grid > :deep(*) {
  animation: card-fade-in 0.4s cubic-bezier(0.4, 0, 0.2, 1) backwards;
}

.results-grid > :deep(*:nth-child(1)) { animation-delay: 0.05s; }
.results-grid > :deep(*:nth-child(2)) { animation-delay: 0.1s; }
.results-grid > :deep(*:nth-child(3)) { animation-delay: 0.15s; }
.results-grid > :deep(*:nth-child(4)) { animation-delay: 0.2s; }
.results-grid > :deep(*:nth-child(5)) { animation-delay: 0.25s; }
.results-grid > :deep(*:nth-child(6)) { animation-delay: 0.3s; }
.results-grid > :deep(*:nth-child(n+7)) { animation-delay: 0.35s; }

@keyframes card-fade-in {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ========================================
   Versions Header
   ======================================== */
.versions-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 1;
  animation: slide-down 0.3s ease-out;
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.versions-header :deep(.n-button) {
  transition: all 0.2s ease;
}

.versions-header :deep(.n-button:hover) {
  color: var(--gold-accent) !important;
}

.versions-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.95);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.versions-count {
  font-size: 0.8rem;
  color: rgba(184, 184, 184, 0.65);
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 10px;
  border-radius: 12px;
}

/* ========================================
   Versions Table Section
   ======================================== */
.versions-section {
  background: rgba(28, 28, 28, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 14px;
  position: relative;
  z-index: 1;
  animation: fade-scale-in 0.3s ease-out;
}

@keyframes fade-scale-in {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Table styling overrides */
.versions-section :deep(.n-data-table) {
  --n-th-color: rgba(36, 36, 36, 0.6) !important;
  --n-td-color: transparent !important;
  --n-td-color-hover: rgba(80, 0, 0, 0.08) !important;
  --n-border-color: rgba(255, 255, 255, 0.04) !important;
}

.versions-section :deep(.n-data-table-th) {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(184, 184, 184, 0.6) !important;
  font-weight: 500;
}

.versions-section :deep(.n-data-table-td) {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.85);
  transition: background 0.2s ease;
}

.versions-section :deep(.n-data-table-tr) {
  transition: all 0.2s ease;
}

.versions-section :deep(.n-data-table-tr:hover) {
  background: rgba(80, 0, 0, 0.06) !important;
}

/* MAM link styling */
.versions-section :deep(.mam-link) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: rgba(184, 184, 184, 0.6);
  border-radius: 6px;
  transition: all 0.2s ease;
}

.versions-section :deep(.mam-link:hover) {
  color: var(--gold-accent);
  background: rgba(220, 170, 80, 0.1);
}

/* Add button styling in table */
.versions-section :deep(.n-button--primary-type) {
  background: linear-gradient(135deg, rgba(140, 35, 35, 0.9) 0%, rgba(90, 21, 21, 0.9) 100%) !important;
  border-color: rgba(180, 60, 60, 0.5) !important;
  box-shadow: 0 2px 8px rgba(100, 20, 20, 0.3);
  transition: all 0.2s ease;
}

.versions-section :deep(.n-button--primary-type:hover:not(:disabled)) {
  background: linear-gradient(135deg, rgba(165, 50, 50, 0.95) 0%, rgba(112, 32, 32, 0.95) 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(120, 30, 30, 0.4);
}

/* ========================================
   Success Banner
   ======================================== */
.success-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  padding: 14px 18px;
  background: linear-gradient(
    135deg,
    rgba(45, 122, 62, 0.12) 0%,
    rgba(35, 100, 50, 0.08) 100%
  );
  border: 1px solid rgba(45, 122, 62, 0.3);
  border-radius: 10px;
  color: var(--success-color);
  font-size: 0.88rem;
  font-weight: 500;
  position: relative;
  z-index: 1;
  animation: success-slide-up 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

@keyframes success-slide-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Shimmer effect on success banner */
.success-banner::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(80, 180, 100, 0.1),
    transparent
  );
  animation: success-shimmer 2s ease-in-out infinite;
}

@keyframes success-shimmer {
  0% { left: -100%; }
  50%, 100% { left: 100%; }
}

.success-banner svg {
  flex-shrink: 0;
  animation: check-bounce 0.5s ease-out;
}

@keyframes check-bounce {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

/* ========================================
   Modal Footer
   ======================================== */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.modal-footer :deep(.n-button) {
  min-width: 90px;
}

/* ========================================
   Responsive Adjustments
   ======================================== */
@media (max-width: 767px) {
  .modal-header {
    gap: 8px;
  }

  .header-title {
    font-size: 1.05rem;
  }

  .header-series {
    margin-left: 0;
    width: 100%;
    justify-content: flex-start;
  }

  .versions-header {
    flex-wrap: wrap;
    gap: 10px;
  }

  .versions-title {
    width: 100%;
    order: -1;
    margin-bottom: 4px;
    font-size: 0.9rem;
  }

  .versions-count {
    margin-left: auto;
  }

  .success-banner {
    padding: 12px 14px;
    font-size: 0.85rem;
  }

  .loading-state,
  .error-state,
  .empty-state {
    padding: 40px 20px;
  }
}

/* ========================================
   Scrollbar Styling
   ======================================== */
.modal-content :deep(.n-scrollbar-rail) {
  right: 2px !important;
}

.modal-content :deep(.n-scrollbar-rail__scrollbar) {
  background: rgba(80, 0, 0, 0.4) !important;
  border-radius: 4px !important;
  width: 6px !important;
}

.modal-content :deep(.n-scrollbar-rail__scrollbar:hover) {
  background: rgba(106, 0, 0, 0.6) !important;
}
</style>
