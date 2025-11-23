<template>
  <div class="showcase-view" :class="{ 'detail-active': detailGroup }">
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
          <GlassTitle tag="h2" class="word-wrap-title">{{ detailGroup.display_title }}</GlassTitle>
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
          <!-- Cover Image using CoverImage component -->
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

        <!-- Table Wrapper with NDataTable -->
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
import CoverImage from '@components/CoverImage.vue'
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'
import GlassTitle from '@components/GlassTitle.vue'
import GlassSubtitle from '@components/GlassSubtitle.vue'
import { useApi } from '@composables/useApi'
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'
import { useAddTorrentFlow } from '@composables/useAddTorrentFlow'
import { sanitizeDescription } from '@/utils/sanitize'

const api = useApi()
const route = useRoute()
const router = useRouter()

// Unified add torrent flow
const { addTorrent, isItemLoading } = useAddTorrentFlow()

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

// Description source label
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

// Sanitized description for safe HTML rendering
const sanitizedDescription = computed(() => {
  return sanitizeDescription(detailDescription.value)
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
const detailDescription = ref('')
const descriptionSource = ref('none')
const descriptionLoading = ref(false)
const descriptionCollapsed = ref(true)

// Add torrent handler using shared composable
const handleAddTorrent = async (rowState) => {
  const result = await addTorrent(rowState)
  status.value = result.message
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
  onAdd: handleAddTorrent,
  isItemLoading
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

  // Fetch description using on-demand enrichment (CoverImage component handles cover loading)
  if (group.display_title) {
    descriptionLoading.value = true

    try {
      const data = await api.enrichMetadata({
        title: group.display_title,
        author: group.author || '',
        mam_id: group.mam_id || ''
      })

      // Always set description and source (even if empty)
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

const closeDetail = () => {
  detailGroup.value = null
  detailDescription.value = ''
  descriptionSource.value = 'none'
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
    detailDescription.value = ''
    descriptionCollapsed.value = true

    // Populate versions table with group versions
    setVersionsData(group.versions || [])

    // Scroll to detail view after DOM updates
    await nextTick()
    if (detailElement.value?.$el) {
      detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    // Fetch description using on-demand enrichment (CoverImage component handles cover loading)
    if (group.display_title) {
      descriptionLoading.value = true

      api.enrichMetadata({
        title: group.display_title,
        author: group.author || '',
        mam_id: group.mam_id || ''
      }).then(data => {
        // Always set description and source (even if empty)
        detailDescription.value = data.description || ''
        descriptionSource.value = data.source || 'none'
      }).catch(err => {
        console.warn('Failed to load enriched metadata:', err)
        detailDescription.value = ''
        descriptionSource.value = 'error'
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
    detailDescription.value = ''
    descriptionSource.value = 'none'
    descriptionLoading.value = false
    clearVersionsData()
  }
})
</script>

<style scoped>
.showcase-view {
  width: 100%;
  max-width: 1400px;
  overflow-x: hidden;
  margin: 0 auto;
  padding: var(--spacing-md, 1rem);
  transition: max-width 0.3s ease;
}

/* Full-width detail view */
.showcase-view.detail-active {
  max-width: 100%;
  padding-left: 0;
  padding-right: 0;
}

/* Keep padding on hero panel when detail is active */
.showcase-view.detail-active .hero-panel {
  margin-left: var(--spacing-md, 1rem);
  margin-right: var(--spacing-md, 1rem);
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

/* Description text styling for v-html content */
.description-text {
  color: var(--text-secondary, #e8e8e8);
  line-height: 1.6;
  word-wrap: break-word;
}

.description-text br {
  margin-bottom: 0.5em;
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

  /* Detail Mode: Remove card max-width on mobile, keep page padding */
  .detail-card {
    width: 100%;
    max-width: none;
  }
}

/* Tablet responsive */
@media (min-width: 769px) and (max-width: 1023px) {
  /* Detail Mode: Remove card max-width on tablet, keep page padding */
  .detail-card {
    width: 100%;
    max-width: none;
  }
}
</style>
