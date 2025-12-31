<template>
  <div class="discover-view" :class="{ 'detail-active': detailGroup }">
    <!-- Hero Panel -->
    <n-card class="hero-panel" :bordered="false">
      <n-space vertical :size="24">
        <!-- Header -->
        <div class="hero-header">
          <GlassTitle tag="h1">
            Discover Audiobooks
          </GlassTitle>
          <GlassSubtitle>
            Search and explore audiobooks from MAM
          </GlassSubtitle>
        </div>

        <!-- Search Form -->
        <n-space :size="12" align="end" :wrap="true" class="search-form">
          <div class="search-input-wrapper">
            <GlassSearchBar
              v-model="form.q"
              placeholder="Search title/author/narrator..."
              @search="runSearch"
              @clear="clearSearch"
            />
          </div>

          <!-- View Toggle -->
          <ViewToggle :model-value="viewMode" @update:model-value="setViewMode" />

          <!-- Limit Dropdown -->
          <GlassSelect
            v-model="form.limit"
            :options="currentLimitOptions"
            width="140px"
          />

          <!-- Sort Dropdown (table mode only) -->
          <GlassSelect
            v-if="isTableMode"
            v-model="form.sort"
            :options="SORT_OPTIONS"
            width="160px"
          />

          <n-button
            type="primary"
            @click="runSearch"
            :loading="loading"
            :disabled="!form.q.trim()"
            class="glass-button-primary"
          >
            <template #icon>
              <span>🔍</span>
            </template>
            Search
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- Status -->
    <n-card v-if="status" class="status-card" :bordered="false">
      <n-text :depth="2">{{ status }}</n-text>
    </n-card>

    <!-- Cards Mode: Showcase Grid -->
    <div v-if="isCardsMode && !detailGroup && cardGroups.length" class="showcase-grid">
      <ShowcaseCard
        v-for="group in cardGroups"
        :key="group.mam_id"
        :group="group"
        @select="showDetail"
      />
    </div>

    <!-- Cards Mode: Detail View -->
    <n-card v-if="isCardsMode && detailGroup" class="detail-card" :bordered="false" ref="detailElement">
      <template #header>
        <n-space justify="space-between" align="center">
          <GlassTitle tag="h2" class="word-wrap-title">{{ detailGroup.display_title }}</GlassTitle>
          <n-space :size="8">
            <n-button secondary @click="searchInTableMode" title="Search all editions in table view">
              ≡ View All Editions
            </n-button>
            <n-button @click="closeDetail" quaternary circle>
              <template #icon>
                <span style="font-size: 18px">✕</span>
              </template>
            </n-button>
          </n-space>
        </n-space>
      </template>

      <div class="detail-content">
        <!-- Cover and Info -->
        <n-space :size="24" align="start">
          <div v-if="detailGroup.mam_id" class="detail-cover-wrapper">
            <CoverImage
              :mam-id="detailGroup.mam_id"
              :title="detailGroup.display_title"
              :author="detailGroup.author || ''"
              :width="200"
              :height="300"
              priority="high"
            />
          </div>

          <n-space vertical :size="12" class="detail-info">
            <div v-if="detailGroup.author">
              <n-text :depth="3" strong>Author:</n-text>
              <n-text :depth="2"> {{ detailGroup.author }}</n-text>
            </div>
            <div v-if="detailGroup.narrator">
              <n-text :depth="3" strong>Narrator:</n-text>
              <n-text :depth="2"> {{ detailGroup.narrator }}</n-text>
            </div>
            <div v-if="detailGroup.formats && detailGroup.formats.length">
              <n-space :size="6">
                <n-tag
                  v-for="format in detailGroup.formats"
                  :key="format"
                  type="primary"
                  size="small"
                  :bordered="false"
                >
                  {{ format }}
                </n-tag>
              </n-space>
            </div>

            <!-- Description -->
            <div class="description-section">
              <n-card :bordered="false" embedded class="description-card">
                <template #header>
                  <n-skeleton v-if="descriptionLoading" text width="40%" />
                  <n-text v-else tag="strong" :depth="2">Description</n-text>
                </template>

                <n-skeleton v-if="descriptionLoading" text :repeat="4" />
                <template v-else-if="detailDescription">
                  <div
                    :class="{ 'description-collapsed': descriptionCollapsed }"
                    class="description-text"
                    v-html="sanitizedDescription"
                  ></div>
                  <n-button
                    v-if="detailDescription.length > 200"
                    text
                    type="primary"
                    size="small"
                    @click="descriptionCollapsed = !descriptionCollapsed"
                    style="margin-top: 8px"
                  >
                    {{ descriptionCollapsed ? 'Show more' : 'Show less' }}
                  </n-button>
                  <n-text :depth="3" style="font-size: 11px; font-style: italic; display: block; margin-top: 8px">
                    {{ descriptionSourceLabel }}
                  </n-text>
                </template>
                <n-text v-else :depth="3" style="font-style: italic">
                  {{ descriptionSourceLabel }}
                </n-text>
              </n-card>
            </div>
          </n-space>
        </n-space>

        <!-- Versions Table -->
        <n-divider />
        <n-text tag="h3" :depth="1" style="margin-bottom: 16px">
          Available Versions ({{ detailGroup.total_versions }})
        </n-text>

        <n-data-table
          ref="versionsTableRef"
          :columns="versionsColumns"
          :data="versionsData"
          :pagination="versionsPagination"
          :bordered="false"
          :single-line="false"
          striped
          class="versions-data-table"
        />
      </div>
    </n-card>

    <!-- Table Mode: Data Table -->
    <div v-if="isTableMode" class="glass-table-wrapper w-full max-w-full overflow-x-hidden">
      <n-data-table
        ref="tableRef"
        :columns="columns"
        :data="tableData"
        :pagination="pagination"
        :bordered="false"
        :loading="loading"
        :single-line="false"
        striped
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NSpace,
  NText,
  NButton,
  NTag,
  NDivider,
  NDataTable,
  NSkeleton
} from 'naive-ui'

// Components
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'
import GlassTitle from '@components/GlassTitle.vue'
import GlassSubtitle from '@components/GlassSubtitle.vue'
import ViewToggle from '@components/ViewToggle.vue'
import ShowcaseCard from '@components/ShowcaseCard.vue'
import CoverImage from '@components/CoverImage.vue'

// Composables
import { useApi } from '@composables/useApi'
import { useViewToggle, VIEW_MODES } from '@composables/useViewToggle'
import { useDiscoverSearch, SORT_OPTIONS } from '@composables/useDiscoverSearch'
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'
import { useAddTorrentFlow } from '@composables/useAddTorrentFlow'
import { sanitizeDescription } from '@/utils/sanitize'

const api = useApi()
const route = useRoute()
const router = useRouter()

// View toggle
const {
  viewMode,
  isCardsMode,
  isTableMode,
  initFromRoute: initViewFromRoute,
  setViewMode
} = useViewToggle({ defaultMode: VIEW_MODES.CARDS })

// Search state - unified API: both cardGroups and tableResults populated from single call
const {
  form,
  loading,
  status,
  tableResults,
  cardGroups,
  totalGroups,
  totalResults,
  detailGroup,
  currentLimitOptions,
  syncFromRoute,
  runSearch: doSearch,
  clearSearch,
  showDetail: doShowDetail,
  closeDetail: doCloseDetail,
  restoreDetailFromUrl
} = useDiscoverSearch({ viewMode })

// Unified add torrent flow
const { addTorrent, isItemLoading } = useAddTorrentFlow()

// Table mode: data table
const {
  tableRef,
  data: tableData,
  columns,
  pagination,
  setData: setTableData,
  clearData: clearTableData,
  sort
} = useMAMSearchDataTable({
  viewType: 'search',
  defaultPageSize: 25,
  onAdd: handleAddTorrent,
  isItemLoading
})

// Keep the data-table source in sync with search results.
// This prevents the table view from looking empty/stale when switching modes.
watch(
  tableResults,
  (results) => {
    setTableData(results)
  },
  { immediate: true }
)

// Detail mode: versions table
const {
  tableRef: versionsTableRef,
  data: versionsData,
  columns: versionsColumns,
  pagination: versionsPagination,
  setData: setVersionsData,
  clearData: clearVersionsData
} = useMAMSearchDataTable({
  viewType: 'search',
  defaultPageSize: 10,
  onAdd: handleAddTorrent,
  isItemLoading
})

// Detail state
const detailElement = ref(null)
const detailDescription = ref('')
const descriptionSource = ref('none')
const descriptionLoading = ref(false)
const descriptionCollapsed = ref(true)

// Computed
const descriptionSourceLabel = computed(() => {
  const sourceMap = {
    'audible': 'via Audible',
    'google': 'via Google Books',
    'openlibrary': 'via Open Library',
    'abs': 'via Audiobookshelf',
    'hardcover': 'via Hardcover',
    'none': 'No metadata available',
    'error': 'Failed to load metadata'
  }
  return sourceMap[descriptionSource.value] || 'Unknown source'
})

const sanitizedDescription = computed(() => {
  return sanitizeDescription(detailDescription.value)
})

// Methods
async function handleAddTorrent(rowState) {
  const result = await addTorrent(rowState)
  status.value = result.message
}

async function runSearch(options = {}) {
  const { silent = false } = options

  await doSearch({ silent })

  // Apply sort for table view after search completes
  if (isTableMode.value) {
    await nextTick()

    if (form.sort === 'seedersDesc') {
      sort('seeders', 'descend')
    } else if (form.sort === 'dateDesc') {
      sort('added', 'descend')
    } else if (form.sort === 'sizeDesc') {
      sort('size', 'descend')
    }
  }
}

async function showDetail(group) {
  doShowDetail(group)
  setVersionsData(group.versions || [])

  // Scroll to detail
  await nextTick()
  if (detailElement.value?.$el) {
    detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // Fetch description
  if (group.display_title) {
    descriptionLoading.value = true
    descriptionCollapsed.value = true

    try {
      const data = await api.enrichMetadata({
        title: group.display_title,
        author: group.author || '',
        mam_id: group.mam_id || ''
      })
      detailDescription.value = data.description || ''
      descriptionSource.value = data.source || 'none'
    } catch (err) {
      console.warn('Failed to load enriched metadata:', err)
      detailDescription.value = ''
      descriptionSource.value = 'error'
    } finally {
      descriptionLoading.value = false
    }
  }
}

function closeDetail() {
  doCloseDetail()
  detailDescription.value = ''
  descriptionSource.value = 'none'
  descriptionLoading.value = false
  clearVersionsData()
}

async function searchInTableMode() {
  if (!detailGroup.value?.display_title) return

  const titleToSearch = detailGroup.value.display_title

  // Close detail
  closeDetail()

  // Switch to table mode and search for this specific title
  form.q = titleToSearch
  setViewMode(VIEW_MODES.TABLE)

  // Trigger search with the specific title
  await runSearch()
}

// Watch view mode changes
// With unified search, both result sets are always populated - no re-search needed
watch(viewMode, (newMode, oldMode) => {
  if (newMode === oldMode) return

  // Clear mode-specific UI state only
  if (newMode === VIEW_MODES.TABLE) {
    clearVersionsData()
    detailDescription.value = ''
  }
  // Note: Don't clear tableData - it's derived from cardGroups and already populated
  // No re-search needed - tableResults and cardGroups are always in sync
})

// Watch for detail parameter changes
watch(() => route.query.detail, async (newDetail, oldDetail) => {
  if (!isCardsMode.value) return

  if (newDetail && newDetail !== oldDetail && cardGroups.value.length) {
    // Find and show the group
    const group = cardGroups.value.find(g =>
      g.normalized_title === newDetail ||
      g.display_title?.toLowerCase().replace(/\s+/g, '-') === newDetail
    )
    if (group) {
      await showDetail(group)
    }
  } else if (!newDetail && oldDetail) {
    closeDetail()
  }
})

// Initialize on mount
onMounted(async () => {
  initViewFromRoute()
  syncFromRoute()

  if (form.q) {
    await runSearch({ silent: true })

    // Restore detail if in URL
    if (isCardsMode.value && route.query.detail) {
      restoreDetailFromUrl()
      if (detailGroup.value) {
        await showDetail(detailGroup.value)
      }
    }
  }
})

// Watch for URL query changes
watch(() => [route.query.q, route.query.limit, route.query.sort], () => {
  // Skip if we're in the middle of a search - prevents race condition
  // where updateUrl() triggers this watcher and interferes with results
  if (loading.value) return

  const previousQuery = form.q
  syncFromRoute()

  if (form.q && form.q !== previousQuery) {
    runSearch({ silent: true })
  }

  if (!form.q) {
    clearTableData()
    status.value = 'Enter a search query to get started.'
  }
})
</script>

<style scoped>
.discover-view {
  width: 100%;
  max-width: 1400px;
  overflow-x: hidden;
  margin: 0 auto;
  padding: var(--spacing-md, 1rem);
  transition: max-width 0.3s ease;
}

.discover-view.detail-active {
  max-width: 100%;
  padding-left: 0;
  padding-right: 0;
}

.discover-view.detail-active .hero-panel {
  margin-left: var(--spacing-md, 1rem);
  margin-right: var(--spacing-md, 1rem);
}

/* Hero Panel */
.hero-panel {
  background: linear-gradient(135deg, rgba(80, 0, 0, 0.15) 0%, rgba(0, 0, 0, 0.8) 100%);
  border-radius: 16px;
  margin-bottom: var(--spacing-lg, 1.5rem);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.hero-header {
  text-align: center;
  padding: var(--spacing-md, 1rem) 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm, 0.5rem);
}

.search-form {
  width: 100%;
}

.search-input-wrapper {
  flex: 1;
  min-width: 200px;
}

/* Status Card */
.status-card {
  margin-bottom: var(--spacing-lg, 1.5rem);
  background: rgba(36, 36, 36, 0.5);
  border-radius: 8px;
}

/* Showcase Grid */
.showcase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--spacing-lg, 1.5rem);
  margin-top: var(--spacing-lg, 1.5rem);
}

/* Detail Card */
.detail-card {
  margin-top: var(--spacing-xl, 2rem);
  background: rgba(0, 0, 0, 0.9);
  border: 2px solid rgba(80, 0, 0, 0.5);
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}

.detail-content {
  padding: var(--spacing-md, 1rem);
}

.detail-cover-wrapper {
  width: 200px;
  height: 300px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.6);
  background: var(--bg-primary, #1a1a1a);
  flex-shrink: 0;
}

.detail-info {
  flex: 1;
}

.description-section {
  margin-top: var(--spacing-md, 1rem);
}

.description-card {
  background: rgba(42, 42, 42, 0.5);
  border-radius: 8px;
}

.description-collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.description-text {
  color: var(--text-secondary, #e8e8e8);
  line-height: 1.6;
  word-wrap: break-word;
}

.versions-data-table {
  margin-top: var(--spacing-md, 1rem);
}

/* Table wrapper */
.glass-table-wrapper {
  margin-top: var(--spacing-lg, 1.5rem);
}

/* Responsive */
@media (max-width: 768px) {
  .search-input-wrapper {
    min-width: 150px;
    width: 100%;
  }

  .showcase-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: var(--spacing-md, 1rem);
  }

  .detail-cover-wrapper {
    width: 100%;
    max-width: 300px;
    align-self: center;
  }

  .detail-card {
    width: 100%;
    max-width: none;
  }

  .glass-table-wrapper {
    margin-left: calc(-1 * var(--spacing-md, 1rem));
    margin-right: calc(-1 * var(--spacing-md, 1rem));
  }
}

@media (min-width: 769px) and (max-width: 1023px) {
  .detail-card {
    width: 100%;
    max-width: none;
  }
}
</style>
