<template>
  <div class="showcase-view">
    <!-- Hero Panel - Audible/Jellyseerr Style -->
    <n-card class="hero-panel" :bordered="false">
      <n-space vertical :size="24">
        <!-- Hero Header -->
        <div class="hero-header">
          <GlassTitle tag="h1">
            Audiobook Showcase
          </GlassTitle>
          <GlassSubtitle>
            Discover audiobooks grouped by title with advanced search powered by Naive UI components
          </GlassSubtitle>
        </div>

        <!-- Search Form -->
        <n-space :size="12" align="end" :wrap="true">
          <div class="search-input-wrapper">
            <GlassSearchBar
              v-model="form.q"
              placeholder="Search audiobooks..."
              @search="runSearch"
              @clear="clearSearch"
            />
          </div>

          <GlassSelect
            v-model="form.limit"
            :options="limitOptions"
            width="140px"
          />

          <n-button
            type="primary"
            size="medium"
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

    <!-- Status Text with Naive UI Typography -->
    <n-card v-if="status" class="status-card" :bordered="false">
      <n-text :depth="2">{{ status }}</n-text>
    </n-card>

    <!-- Showcase Grid -->
    <div v-if="!detailGroup && groups.length" class="showcase-grid">
      <ShowcaseCard v-for="group in groups" :key="group.mam_id" :group="group" @select="showDetail" />
    </div>

    <!-- Detail View with Naive UI Cards -->
    <n-card v-if="detailGroup" class="detail-card" :bordered="false" ref="detailElement">
      <template #header>
        <n-space justify="space-between" align="center">
          <GlassTitle tag="h2">{{ detailGroup.display_title }}</GlassTitle>
          <n-space :size="8">
            <n-button secondary @click="searchThisTitle" title="Search MAM for this title (25 results)">
              🔍 Search MAM
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
        <!-- Cover and Info Section -->
        <n-space :size="24" align="start">
          <!-- Cover Image -->
          <div v-if="detailGroup.mam_id" class="detail-cover-wrapper">
            <img
              v-if="detailCoverUrl"
              :src="detailCoverUrl"
              :alt="detailGroup.display_title"
              loading="lazy"
              class="detail-cover"
            />
            <div v-else class="cover-skeleton">
              <n-spin size="small" />
            </div>
          </div>

          <!-- Info Section -->
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

            <!-- Description - Lazy Loading Card -->
            <div class="description-section">
              <n-card :bordered="false" embedded class="description-card">
                <template #header>
                  <n-skeleton v-if="descriptionLoading" text width="40%" />
                  <n-text v-else tag="strong" :depth="2">
                    Description
                  </n-text>
                </template>

                <n-skeleton v-if="descriptionLoading" text :repeat="4" />
                <template v-else-if="detailDescription">
                  <div :class="{ 'description-collapsed': descriptionCollapsed }">
                    <n-text :depth="2">{{ detailDescription }}</n-text>
                  </div>
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
                    via Audiobookshelf
                  </n-text>
                </template>
                <n-text v-else :depth="3" style="font-style: italic">
                  No description available
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

        <!-- Table Wrapper with NDataTable -->
        <n-data-table
          ref="versionsTableRef"
          :columns="versionsColumns"
          :data="versionsData"
          :pagination="versionsPagination"
          :bordered="false"
          :scroll-x="1400"
          striped
          class="versions-data-table"
        />
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBreakpoints } from '@vueuse/core'
import {
  NCard,
  NSpace,
  NText,
  NButton,
  NTag,
  NDivider,
  NSpin,
  NDataTable,
  NSkeleton
} from 'naive-ui'
import ShowcaseCard from '@components/ShowcaseCard.vue'
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'
import GlassTitle from '@components/GlassTitle.vue'
import GlassSubtitle from '@components/GlassSubtitle.vue'
import { useApi } from '@composables/useApi'
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'

const api = useApi()
const route = useRoute()
const router = useRouter()

// Responsive breakpoints for dynamic input width
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic input width based on screen size
const inputWidth = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return '500px'
  } else if (breakpoints.greater('tablet').value) {
    return '350px'
  } else {
    return '100%'
  }
})

const formRef = ref(null)
const form = reactive({ q: '', limit: '100' })
const limitOptions = [
  { label: '50 results', value: '50' },
  { label: '100 results', value: '100' },
  { label: '200 results', value: '200' },
  { label: '500 results', value: '500' }
]

const status = ref('Enter a search query to find audiobooks.')
const loading = ref(false)
const groups = ref([])
const detailGroup = ref(null)
const detailElement = ref(null)
const detailCoverUrl = ref('')
const detailDescription = ref('')
const descriptionLoading = ref(false)
const descriptionCollapsed = ref(true)

// Add torrent handler - defined before data table initialization
const addTorrent = async (rowState) => {
  try {
    await api.addTorrent({
      id: String(rowState.id ?? ''),
      title: rowState.title || '',
      dl: rowState.dl || '',
      author: rowState.author_info || '',
      narrator: rowState.narrator_info || '',
      abs_cover_url: rowState.abs_cover_url || '',
      abs_item_id: rowState.abs_item_id || ''
    })
    status.value = `✓ Added "${rowState.title}" to qBittorrent`
    window.dispatchEvent(new CustomEvent('torrentAdded'))
  } catch (err) {
    status.value = `Add failed: ${err.message}`
  }
}

// Initialize versions data table with search configuration
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
  onAdd: addTorrent
})

const normalizeQuery = (values) => {
  const query = {}
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query[key] = value
    }
  })
  return query
}

const syncForm = () => {
  const getValue = (key, fallback) => {
    const value = route.query[key]
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? fallback
    }
    return value ?? fallback
  }

  form.q = getValue('q', '')
  form.limit = getValue('limit', '100')
}

const runSearch = async () => {
  if (!form.q.trim()) {
    status.value = 'Enter a search query to find audiobooks.'
    groups.value = []
    detailGroup.value = null
    return
  }
  loading.value = true
  status.value = 'Loading audiobooks…'
  groups.value = []
  detailGroup.value = null

  try {
    const data = await api.getShowcase({ query: form.q.trim(), limit: parseInt(form.limit, 10) })
    groups.value = data.groups || []
    status.value = groups.value.length ? `Showing ${data.total_groups} titles (${data.total_results} versions)` : 'No audiobooks found.'

    // Update URL with search params (preserve detail if exists)
    router.replace({
      query: normalizeQuery({
        q: form.q.trim(),
        limit: form.limit,
        detail: route.query.detail // Preserve detail parameter
      })
    })

    // Restore detail view if detail parameter exists in URL
    if (route.query.detail) {
      restoreDetailFromUrl()
    }
  } catch (err) {
    status.value = `Failed to load showcase: ${err.message}`
  } finally {
    loading.value = false
  }
}

const clearSearch = () => {
  form.q = ''
  groups.value = []
  detailGroup.value = null
  status.value = 'Enter a search query to find audiobooks.'
}

const showDetail = async (group) => {
  console.log('showDetail called with:', group)
  detailGroup.value = group
  detailCoverUrl.value = ''
  detailDescription.value = ''
  descriptionCollapsed.value = true

  // Populate versions table with group versions
  setVersionsData(group.versions || [])

  // Update URL with detail parameter
  router.push({
    query: {
      ...route.query,
      detail: group.normalized_title || group.display_title?.toLowerCase().replace(/\s+/g, '-') || 'unknown'
    }
  })

  // Scroll to detail view after DOM updates
  await nextTick()
  if (detailElement.value?.$el) {
    detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  // Load cover and description separately for lazy loading effect
  if (group.mam_id && group.display_title) {
    // Start description loading
    descriptionLoading.value = true

    try {
      const data = await api.fetchCover({
        mam_id: group.mam_id,
        title: group.display_title,
        author: group.author || '',
        max_retries: '3'
      })

      // Set cover URL
      detailCoverUrl.value = data.cover_url || ''

      // Set description if available
      if (data.description) {
        detailDescription.value = data.description
      }
    } catch (err) {
      console.warn('Failed to load detail cover and description:', err)
    } finally {
      // Stop loading after fetch completes
      descriptionLoading.value = false
    }
  }
}

const closeDetail = () => {
  detailGroup.value = null
  detailCoverUrl.value = ''
  detailDescription.value = ''
  descriptionLoading.value = false
  clearVersionsData()

  // Remove detail parameter from URL
  const query = { ...route.query }
  delete query.detail
  router.replace({ query })
}

const searchThisTitle = () => {
  if (!detailGroup.value?.display_title) return

  // Capture title before closing detail view
  const titleToSearch = detailGroup.value.display_title

  // Close detail view
  detailGroup.value = null
  detailCoverUrl.value = ''
  detailDescription.value = ''

  // Set search parameters
  form.q = titleToSearch
  form.limit = '25'

  // Run the search
  runSearch()
}

const restoreDetailFromUrl = async () => {
  const detailId = route.query.detail
  if (!detailId || !groups.value.length) return

  // Find matching group by normalized_title
  const group = groups.value.find(g =>
    g.normalized_title === detailId ||
    g.display_title?.toLowerCase().replace(/\s+/g, '-') === detailId
  )

  if (group) {
    // Show detail without updating URL (already in URL)
    detailGroup.value = group
    detailCoverUrl.value = ''
    detailDescription.value = ''
    descriptionCollapsed.value = true

    // Populate versions table with group versions
    setVersionsData(group.versions || [])

    // Scroll to detail view after DOM updates
    await nextTick()
    if (detailElement.value?.$el) {
      detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    // Load cover and description with loading state
    if (group.mam_id && group.display_title) {
      descriptionLoading.value = true

      api.fetchCover({
        mam_id: group.mam_id,
        title: group.display_title,
        author: group.author || '',
        max_retries: '3'
      }).then(data => {
        detailCoverUrl.value = data.cover_url || ''
        if (data.description) {
          detailDescription.value = data.description
        }
      }).catch(err => {
        console.warn('Failed to load detail cover and description:', err)
      }).finally(() => {
        descriptionLoading.value = false
      })
    }
  }
}

onMounted(() => {
  syncForm()
  if (form.q) {
    runSearch()
  }
})

// Watch for search parameter changes
watch(() => [route.query.q, route.query.limit], () => {
  const previous = form.q
  syncForm()
  if (form.q && form.q !== previous) {
    runSearch()
  }
  if (!form.q) {
    groups.value = []
    detailGroup.value = null
    status.value = 'Enter a search query to find audiobooks.'
  }
})

// Watch for detail parameter changes (browser back/forward)
watch(() => route.query.detail, (newDetail, oldDetail) => {
  if (newDetail && newDetail !== oldDetail) {
    // Detail parameter added or changed - show detail view
    restoreDetailFromUrl()
  } else if (!newDetail && oldDetail) {
    // Detail parameter removed - close detail view
    detailGroup.value = null
    detailCoverUrl.value = ''
    detailDescription.value = ''
    descriptionLoading.value = false
    clearVersionsData()
  }
})
</script>

<style scoped>
.showcase-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--spacing-md, 1rem);
}

/* Hero Panel - Audible/Jellyseerr Inspired */
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

/* Title styles now handled by GlassTitle/GlassSubtitle components */

/* Make search input responsive */
.search-input-wrapper {
  flex: 1;
  min-width: 200px;
}

@media (max-width: 768px) {
  .search-input-wrapper {
    min-width: 150px;
    width: 100%;
  }
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

/* Detail title styles now handled by GlassTitle component */

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

.detail-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-skeleton {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    90deg,
    rgba(36, 36, 36, 0.5) 0%,
    rgba(42, 42, 42, 0.5) 50%,
    rgba(36, 36, 36, 0.5) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
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

/* Versions Data Table */
.versions-data-table {
  margin-top: var(--spacing-md, 1rem);
}

/* Responsive */
@media (max-width: 768px) {
  .showcase-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: var(--spacing-md, 1rem);
  }

  .detail-cover-wrapper {
    width: 100%;
    max-width: 300px;
    align-self: center;
  }
}
</style>
