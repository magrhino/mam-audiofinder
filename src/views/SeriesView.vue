<template>
  <div class="series-view">
    <!-- Hero Panel - Glassmorphism Style -->
    <n-card class="hero-panel" :bordered="false">
      <n-space vertical :size="24">
        <!-- Hero Header -->
        <div class="hero-header">
          <GlassTitle tag="h1">
            Series Discovery
          </GlassTitle>
          <GlassSubtitle>
            Discover audiobook series powered by Hardcover API
          </GlassSubtitle>
        </div>

        <!-- Search Form -->
        <n-space :size="12" align="end" :wrap="true">
          <div class="search-input-wrapper">
            <GlassSearchBar
              v-model="form.title"
              placeholder="Search by title..."
              @search="runSearch"
            />
          </div>

          <div class="author-input-wrapper">
            <GlassSearchBar
              v-model="form.author"
              placeholder="Author (optional)..."
              @search="runSearch"
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
            :disabled="!form.title.trim()"
            class="glass-button-primary"
          >
            <template #icon>
              <span>🔍</span>
            </template>
            Search Series
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <!-- Status Card -->
    <n-card v-if="status" class="status-card" :bordered="false">
      <n-text :depth="2">{{ status }}</n-text>
    </n-card>

    <!-- Series Results Table -->
    <div v-if="!detailItem && results.length" class="table-wrapper">
      <n-data-table
        ref="seriesTableRef"
        :columns="seriesColumns"
        :data="results"
        :pagination="seriesPagination"
        :bordered="false"
        :scroll-x="scrollX"
        striped
      />
    </div>

    <!-- Detail View -->
    <n-card v-if="detailItem" class="detail-card" :bordered="false" ref="detailElement">
      <template #header>
        <n-space justify="space-between" align="center">
          <GlassTitle tag="h2">{{ detailItem.series_name }}</GlassTitle>
          <n-button @click="closeDetail" quaternary circle>
            <template #icon>
              <span style="font-size: 18px">✕</span>
            </template>
          </n-button>
        </n-space>
      </template>

      <div class="detail-content">
        <!-- Series Metadata -->
        <n-space :size="12" style="margin-bottom: 1.5rem">
          <n-tag v-if="detailItem.author_name" type="info" :bordered="false" size="medium">
            📝 {{ detailItem.author_name }}
          </n-tag>
          <n-tag type="default" :bordered="false" size="medium">
            📚 {{ detailItem.book_count || 0 }} books
          </n-tag>
          <n-tag v-if="detailItem.readers_count" type="success" :bordered="false" size="medium">
            📖 {{ detailItem.readers_count.toLocaleString() }} readers
          </n-tag>
        </n-space>

        <n-divider />

        <!-- Books Table -->
        <n-text tag="h3" :depth="1" style="margin-bottom: 16px">
          Books in Series
        </n-text>

        <n-data-table
          ref="booksTableRef"
          :columns="booksColumns"
          :data="booksData"
          :pagination="booksPagination"
          :bordered="false"
          :scroll-x="scrollX"
          striped
          class="books-table"
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
  NDataTable
} from 'naive-ui'
import { useApi } from '@composables/useApi'
import { useSeriesDataTable, useBooksDataTable } from '@composables/naive/useSeriesDataTable'
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'
import GlassTitle from '@components/GlassTitle.vue'
import GlassSubtitle from '@components/GlassSubtitle.vue'

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
    return '400px'
  } else if (breakpoints.greater('tablet').value) {
    return '300px'
  } else {
    return '100%'
  }
})

// Dynamic scroll-x for responsive tables
const scrollX = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 1000
  } else if (breakpoints.greater('tablet').value) {
    return 900
  } else {
    return 700
  }
})

// Form configuration
const formRef = ref(null)
const form = reactive({ title: '', author: '', limit: '20' })
const limitOptions = [
  { label: '5 results', value: '5' },
  { label: '10 results', value: '10' },
  { label: '20 results', value: '20' },
  { label: '30 results', value: '30' },
  { label: '40 results', value: '40' },
  { label: '50 results', value: '50' }
]

const status = ref('Search for a title to see matching series.')
const loading = ref(false)
const results = ref([])

// Detail view state
const detailItem = ref(null)
const detailElement = ref(null)

const scrollToDetailCard = async () => {
  await nextTick()
  if (detailElement.value?.$el) {
    detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Initialize series results table
const {
  tableRef: seriesTableRef,
  columns: seriesColumns,
  pagination: seriesPagination
} = useSeriesDataTable({
  onSelect: loadDetail,
  defaultPageSize: 20
})

// Initialize books table
const {
  tableRef: booksTableRef,
  data: booksData,
  columns: booksColumns,
  pagination: booksPagination,
  setData: setBooksData,
  clearData: clearBooksData
} = useBooksDataTable({
  defaultPageSize: 10
})

// URL parameter handling helpers
const normalizeQuery = (values) => {
  const query = {}
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query[key] = value
    }
  })
  return query
}

const getQueryValue = (value, fallback = undefined) => {
  if (Array.isArray(value)) {
    return value[value.length - 1] ?? fallback
  }
  return value ?? fallback
}

// Sync form with URL query parameters
const syncForm = () => {
  form.title = getQueryValue(route.query.title, '')
  form.author = getQueryValue(route.query.author, '')
  form.limit = getQueryValue(route.query.limit, '20')
}

// Run series search
const runSearch = async () => {
  if (!form.title.trim()) {
    status.value = 'Please enter a book title.'
    results.value = []
    detailItem.value = null
    return
  }

  loading.value = true
  status.value = 'Searching for series…'
  detailItem.value = null
  clearBooksData()

  try {
    const data = await api.searchSeries({
      title: form.title.trim(),
      author: form.author.trim(),
      limit: parseInt(form.limit, 10)
    })

    results.value = data.hardcover_series || []
    status.value = results.value.length
      ? `Found ${results.value.length} series`
      : 'No series found.'

    // Update URL with search parameters
    const detailParam = getQueryValue(route.query.detail)
    router.replace({
      name: 'series',
      query: normalizeQuery({
        title: form.title.trim(),
        author: form.author.trim(),
        limit: form.limit,
        detail: detailParam
      })
    })

    if (detailParam) {
      await restoreDetailFromUrl()
    }
  } catch (err) {
    status.value = `Series search failed: ${err.message}`
  } finally {
    loading.value = false
  }
}

// Clear search
const clearSearch = () => {
  form.title = ''
  form.author = ''
  results.value = []
  detailItem.value = null
  clearBooksData()
  status.value = 'Search for a title to see matching series.'
}

// Load series detail
async function loadDetail(series, options = {}) {
  const { suppressNavigation = false } = options
  status.value = 'Loading series books…'
  detailItem.value = series
  clearBooksData()
  await scrollToDetailCard()

  if (!suppressNavigation) {
    router.push({
      name: 'series',
      query: {
        ...route.query,
        detail: String(series.series_id)
      }
    })
  }

  try {
    const data = await api.getSeriesBooks(series.series_id)

    // Set books data
    setBooksData(data.books || [])

    status.value = `${data.books?.length || 0} books in this series`
  } catch (err) {
    status.value = `Failed to load series: ${err.message}`
  }
}

// Close detail view
const closeDetail = (options = {}) => {
  const { suppressNavigation = false } = options
  detailItem.value = null
  clearBooksData()
  status.value = results.value.length
    ? `Found ${results.value.length} series`
    : 'Search for a title to see matching series.'

  if (!suppressNavigation) {
    const query = { ...route.query }
    delete query.detail
    router.replace({
      name: 'series',
      query
    })
  }
}

async function restoreDetailFromUrl() {
  const detailId = getQueryValue(route.query.detail)
  if (!detailId || !results.value.length) {
    return
  }

  const match = results.value.find(
    (series) => String(series.series_id) === String(detailId)
  )

  if (match) {
    await loadDetail(match, { suppressNavigation: true })
  }
}

// Lifecycle hooks
onMounted(() => {
  syncForm()
  if (form.title) {
    runSearch()
  }
})

// Watch for URL parameter changes
watch(() => [route.query.title, route.query.author, route.query.limit], () => {
  const previous = form.title
  syncForm()
  if (form.title && form.title !== previous) {
    runSearch()
  }
  if (!form.title) {
    results.value = []
    detailItem.value = null
    status.value = 'Please enter a book title.'
  }
})

// Watch detail query parameter for navigation events (back/forward)
watch(() => route.query.detail, async (newDetail, oldDetail) => {
  const normalizedNew = getQueryValue(newDetail)
  const normalizedOld = getQueryValue(oldDetail)

  if (
    normalizedNew &&
    detailItem.value &&
    String(detailItem.value.series_id) === String(normalizedNew)
  ) {
    return
  }

  if (normalizedNew && normalizedNew !== normalizedOld) {
    await restoreDetailFromUrl()
  } else if (!normalizedNew && normalizedOld && detailItem.value) {
    closeDetail({ suppressNavigation: true })
  }
})
</script>

<style scoped>
.series-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--spacing-md, 1rem);
}

/* Hero Panel - Glassmorphism */
.hero-panel {
  background: linear-gradient(135deg, rgba(80, 0, 0, 0.15) 0%, rgba(0, 0, 0, 0.8) 100%);
  border-radius: 16px;
  margin-bottom: var(--spacing-lg, 1.5rem);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
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

/* Make search inputs responsive */
.search-input-wrapper {
  flex: 1;
  min-width: 250px;
}

.author-input-wrapper {
  min-width: 200px;
}

@media (max-width: 768px) {
  .search-input-wrapper,
  .author-input-wrapper {
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

/* Table Wrapper */
.table-wrapper {
  margin-top: var(--spacing-lg, 1.5rem);
}

/* Detail Card - Glassmorphism */
.detail-card {
  margin-top: var(--spacing-xl, 2rem);
  background: rgba(0, 0, 0, 0.9);
  border: 2px solid rgba(80, 0, 0, 0.5);
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
}

/* Detail title styles now handled by GlassTitle component */

.detail-content {
  padding: var(--spacing-md, 1rem);
}

.books-table {
  margin-top: var(--spacing-md, 1rem);
}

/* Responsive */
@media (max-width: 768px) {
  .search-input-item {
    min-width: 100%;
  }
}
</style>
