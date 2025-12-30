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
        :single-line="false"
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
        <n-space :size="12" style="margin-bottom: 1.5rem" align="center">
          <n-tag v-if="detailItem.author_name" type="info" :bordered="false" size="medium">
            📝 {{ detailItem.author_name }}
          </n-tag>
          <n-tag type="default" :bordered="false" size="medium">
            📚 {{ detailItem.book_count || 0 }} books
          </n-tag>
          <n-tag v-if="detailItem.readers_count" type="success" :bordered="false" size="medium">
            📖 {{ detailItem.readers_count.toLocaleString() }} readers
          </n-tag>

          <!-- Bulk Audiobook Metadata Fetch Button -->
          <n-button
            v-if="hasUnfetchedAudioMeta && !booksLoading"
            type="primary"
            size="small"
            @click="fetchAudioMetadataForAll"
            :loading="isFetchingAudioMeta"
          >
            <template #icon>
              <span>🎧</span>
            </template>
            Fetch Audiobook Info
          </n-button>

          <!-- Toggle All Editions Button -->
          <n-button
            v-if="!booksLoading"
            type="default"
            size="small"
            @click="toggleAllEditions"
            :loading="isTogglingEditions"
          >
            <template #icon>
              <span>{{ showAllEditions ? '📘' : '🌐' }}</span>
            </template>
            {{ showAllEditions ? 'Show Canonical Only' : 'Show non-English Titles' }}
          </n-button>
        </n-space>

        <n-divider />

        <!-- Enrichment Progress Indicator -->
        <n-card v-if="enrichmentProgress" class="glass-panel" size="small" style="margin-bottom: 1.5rem">
          <n-space align="center" :size="12">
            <n-spin size="small" />
            <n-text style="flex: 1">
              Loading covers and metadata...
              <strong>{{ enrichmentProgress.completed }}/{{ enrichmentProgress.total }}</strong>
            </n-text>
            <n-progress
              type="line"
              :percentage="enrichmentProgress.percentage"
              :show-indicator="false"
              :height="6"
              style="width: 200px"
            />
          </n-space>
        </n-card>

        <!-- Books Grid -->
        <n-space justify="space-between" align="center" style="margin-bottom: 16px">
          <n-text tag="h3" :depth="1">
            Books in Series ({{ booksTotal }})
          </n-text>
          <n-text v-if="booksLoading" :depth="3">Loading...</n-text>
        </n-space>

        <!-- Responsive Card Grid -->
        <div class="books-grid" :style="gridStyle">
          <ShowcaseCard
            v-for="book in paginatedBooks"
            :key="book.normalized_title"
            :group="book"
            :seriesNumber="book.position"
            :hideVersionBadge="true"
            :showCanonicalBadge="showAllEditions"
            @select="handleBookClick"
          />
        </div>

        <!-- Pagination Controls -->
        <n-space justify="center" style="margin-top: 1.5rem" v-if="booksTotalPages > 1">
          <n-button
            secondary
            @click="loadPrevPage"
            :disabled="!hasPrevPage || booksLoading"
          >
            ← Previous
          </n-button>

          <n-text :depth="2">
            Page {{ booksPage }} of {{ booksTotalPages }}
          </n-text>

          <n-button
            secondary
            @click="loadNextPage"
            :disabled="!hasNextPage || booksLoading"
          >
            Next →
          </n-button>
        </n-space>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBreakpoints } from '@/composables/useBreakpoints'
import { useMediaQuery } from '@vueuse/core'
import {
  NCard,
  NSpace,
  NText,
  NButton,
  NTag,
  NDivider,
  NDataTable,
  NSpin,
  NProgress
} from 'naive-ui'
import { useApi } from '@composables/useApi'
import { useSeriesDataTable } from '@composables/naive/useSeriesDataTable'
import { useSeriesCache } from '@composables/useSeriesCache'
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'
import GlassTitle from '@components/GlassTitle.vue'
import GlassSubtitle from '@components/GlassSubtitle.vue'
import ShowcaseCard from '@components/ShowcaseCard.vue'

const api = useApi()
const route = useRoute()
const router = useRouter()
const seriesCache = useSeriesCache()

// Centralized responsive breakpoints
const { isMobile, isTablet, isDesktop } = useBreakpoints()

// Component-specific wide breakpoint (1400px+)
const isWide = useMediaQuery('(min-width: 1400px)')

// Dynamic input width based on screen size
const inputWidth = computed(() => {
  if (isDesktop.value) {
    return '400px'
  } else if (isTablet.value) {
    return '300px'
  } else {
    return '100%'
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

// Books state for card grid
const enrichedBooks = ref([])
const booksTotal = ref(0)
const booksPage = ref(1)
const booksPerPage = ref(20)  // Show 20 books per page (was 5)
const booksTotalPages = ref(0)
const hasNextPage = ref(false)
const hasPrevPage = ref(false)
const booksLoading = ref(false)

// Paginated books - slice enrichedBooks based on current page
const paginatedBooks = computed(() => {
  const start = (booksPage.value - 1) * booksPerPage.value
  const end = start + booksPerPage.value
  return enrichedBooks.value.slice(start, end)
})

// Progressive enrichment state
const enrichmentProgress = ref(null)  // { total, completed, percentage }
const enrichmentStatus = ref(null)    // 'pending', 'in_progress', 'complete', 'failed'
let pollIntervals = []  // Track all polling intervals (safety net for multiple calls)

// Audiobook metadata fetching state
const isFetchingAudioMeta = ref(false)

// All editions toggle state
const showAllEditions = ref(false)
const isTogglingEditions = ref(false)

// Check if any books don't have audiobook metadata yet
const hasUnfetchedAudioMeta = computed(() => {
  return enrichedBooks.value.some(book => book.has_audiobook === undefined)
})

// Guard to prevent duplicate loadDetail() calls from watch cascade
const currentDetailSeriesId = ref(null)

// Responsive grid configuration
const gridColumns = computed(() => {
  if (isWide.value) return 6
  if (isDesktop.value) return 5
  if (isTablet.value) return 4
  return 2
})

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${gridColumns.value}, 1fr)`,
  gap: isDesktop.value ? '1.5rem' : '1rem'
}))

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
  enrichedBooks.value = []

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
  enrichedBooks.value = []
  status.value = 'Search for a title to see matching series.'
}

// Load series detail with progressive enrichment
async function loadDetail(series, options = {}) {
  const { suppressNavigation = false } = options

  // GUARD: Skip if already displaying this exact series (prevents watch cascade)
  if (currentDetailSeriesId.value === String(series.series_id)) {
    console.log(`[SeriesView] Series ${series.series_id} already loaded, skipping duplicate call`)
    return
  }

  currentDetailSeriesId.value = String(series.series_id)
  status.value = 'Loading series books…'
  detailItem.value = series

  // Stop ALL existing polling intervals
  pollIntervals.forEach(id => clearInterval(id))
  pollIntervals = []

  // Reset books state
  enrichedBooks.value = []
  booksPage.value = 1
  booksLoading.value = true
  enrichmentProgress.value = null
  enrichmentStatus.value = null

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
    // Check cache first (with edition mode key)
    const editionMode = showAllEditions.value ? 'all' : 'canonical'
    const cacheKey = `${series.series_id}:${editionMode}`
    const cached = seriesCache.get(cacheKey)

    // Use cached data if enrichment was complete OR still in progress (don't re-fetch)
    if (cached && (
      cached.enrichment_status === 'complete' ||
      cached.enrichment_status === 'in_progress'
    )) {
      console.log(`[SeriesView] Cache HIT for series ${series.series_id} (${editionMode}, status: ${cached.enrichment_status}) - using cached data`)
      enrichedBooks.value = cached.books || []
      booksTotal.value = cached.total || 0
      enrichmentStatus.value = cached.enrichment_status
      enrichmentProgress.value = cached.enrichment_progress
      status.value = `${booksTotal.value} books in this series (from cache)`
      booksLoading.value = false

      // Calculate pagination
      booksTotalPages.value = Math.ceil(booksTotal.value / booksPerPage.value)
      hasNextPage.value = booksPage.value < booksTotalPages.value
      hasPrevPage.value = booksPage.value > 1

      // If still in progress, RESUME polling (don't restart enrichment)
      if (cached.enrichment_status === 'in_progress') {
        enrichmentProgress.value = cached.enrichment_progress
        startEnrichmentPolling(series.series_id)
      } else {
        enrichmentProgress.value = null  // Hide progress bar for completed
      }

      return  // Skip API call
    }

    console.log(`[SeriesView] Cache MISS for series ${series.series_id} (${editionMode}) - fetching from API`)

    // Step 1: Fetch basic book data immediately (with positions and edition filter)
    const data = await api.getSeriesBooks(series.series_id, {
      enrich_mode: 'immediate',  // Progressive loading mode
      showAllEditions: showAllEditions.value
    })

    // Step 2: Display books immediately with basic data
    enrichedBooks.value = (data.books || []).map(book => ({
      ...book,
      // Add placeholder fields if missing
      display_title: book.display_title || book.title,
      cover_url: book.cover_url || '',
      enrichment_pending: !book.cover_url  // Mark as pending if no cover
    }))

    booksTotal.value = data.total || 0
    enrichmentStatus.value = data.enrichment_status
    enrichmentProgress.value = data.enrichment_progress

    // Cache the result (with edition mode key)
    seriesCache.set(cacheKey, {
      books: enrichedBooks.value,
      total: booksTotal.value,
      enrichment_status: enrichmentStatus.value,
      enrichment_progress: enrichmentProgress.value
    })

    // Calculate pagination
    booksTotalPages.value = Math.ceil(booksTotal.value / booksPerPage.value)
    hasNextPage.value = booksPage.value < booksTotalPages.value
    hasPrevPage.value = booksPage.value > 1

    status.value = `${booksTotal.value} books in this series`
    booksLoading.value = false  // Books visible now

    // Step 3: Start polling for enriched data if enrichment is in progress
    if (enrichmentStatus.value === 'pending' || enrichmentStatus.value === 'in_progress') {
      startEnrichmentPolling(series.series_id)
    }

  } catch (err) {
    status.value = `Failed to load series: ${err.message}`
    booksLoading.value = false
  }
}

// Start polling for enrichment status
function startEnrichmentPolling(seriesId) {
  const maxAttempts = 30  // 30 attempts × 2s = 60s max polling
  let attempts = 0

  const intervalId = setInterval(async () => {
    attempts++

    try {
      const statusData = await api.getSeriesBooks(seriesId, {
        enrich_mode: 'status'  // Check enrichment status
      })

      // Update progress
      enrichmentProgress.value = statusData.enrichment_progress
      enrichmentStatus.value = statusData.enrichment_status

      // Merge enriched books (update covers, metadata in place)
      if (statusData.books && statusData.books.length > 0) {
        mergeBooksData(statusData.books)
      }

      // Stop polling when complete, failed, or max attempts reached
      if (
        statusData.enrichment_status === 'complete' ||
        statusData.enrichment_status === 'failed' ||
        statusData.enrichment_status === 'not_found' ||
        attempts >= maxAttempts
      ) {
        clearInterval(intervalId)
        // Remove from tracking array
        pollIntervals = pollIntervals.filter(id => id !== intervalId)
        enrichmentProgress.value = null  // Hide progress bar

        // Update cache with final status
        if (detailItem.value && detailItem.value.series_id) {
          seriesCache.set(detailItem.value.series_id, {
            books: enrichedBooks.value,
            total: booksTotal.value,
            enrichment_status: statusData.enrichment_status,
            enrichment_progress: null
          })
        }

        if (statusData.enrichment_status === 'failed') {
          status.value = `Enrichment failed. Showing basic data only.`
        } else if (statusData.enrichment_status === 'complete') {
          status.value = `${booksTotal.value} books in this series (fully loaded)`
        }
      }

    } catch (err) {
      console.error('[SeriesView] Enrichment polling error:', err)
      // Continue polling despite errors (API might be temporarily unavailable)
    }

  }, 2000)  // Poll every 2 seconds

  // Track this interval
  pollIntervals.push(intervalId)
}

// Merge enriched book data into existing books array
function mergeBooksData(newBooks) {
  // Use cache merge if we have detailItem (series_id available)
  if (detailItem.value && detailItem.value.series_id) {
    // Try to merge via cache (with edition mode key)
    const editionMode = showAllEditions.value ? 'all' : 'canonical'
    const cacheKey = `${detailItem.value.series_id}:${editionMode}`
    const merged = seriesCache.mergeBooksData(cacheKey, newBooks)

    if (merged) {
      // Cache merge succeeded, retrieve updated data
      const cached = seriesCache.get(cacheKey)
      if (cached && cached.books) {
        enrichedBooks.value = cached.books
        return
      }
    }
  }

  // Fallback to local merge if cache merge failed
  enrichedBooks.value = enrichedBooks.value.map(existingBook => {
    // Find matching enriched book by title + author
    const enriched = newBooks.find(b =>
      (b.display_title === existingBook.display_title || b.title === existingBook.title) &&
      b.author === existingBook.author
    )

    if (enriched) {
      // Merge enriched data (covers, metadata, etc.)
      return {
        ...existingBook,
        ...enriched,
        enrichment_pending: false  // Mark as enriched
      }
    }

    return existingBook  // Keep existing data if no match
  })
}

// Toggle between canonical and all editions
async function toggleAllEditions() {
  if (!detailItem.value || isTogglingEditions.value) return

  isTogglingEditions.value = true
  showAllEditions.value = !showAllEditions.value

  try {
    // Stop ALL existing polling intervals
    pollIntervals.forEach(id => clearInterval(id))
    pollIntervals = []

    // Reset books state
    enrichedBooks.value = []
    booksPage.value = 1
    booksLoading.value = true
    enrichmentProgress.value = null
    enrichmentStatus.value = null

    const seriesId = detailItem.value.series_id
    const editionMode = showAllEditions.value ? 'all' : 'canonical'

    console.log(`[SeriesView] Toggling to ${editionMode} editions for series ${seriesId}`)

    // Fetch with new showAllEditions parameter
    const data = await api.getSeriesBooks(seriesId, {
      enrich_mode: 'immediate',
      showAllEditions: showAllEditions.value
    })

    // Display books immediately with basic data
    enrichedBooks.value = (data.books || []).map(book => ({
      ...book,
      display_title: book.display_title || book.title,
      cover_url: book.cover_url || '',
      enrichment_pending: !book.cover_url
    }))

    booksTotal.value = data.total || 0
    enrichmentStatus.value = data.enrichment_status
    enrichmentProgress.value = data.enrichment_progress

    // Cache the result (with edition mode key)
    const cacheKey = `${seriesId}:${editionMode}`
    seriesCache.set(cacheKey, {
      books: enrichedBooks.value,
      total: booksTotal.value,
      enrichment_status: enrichmentStatus.value,
      enrichment_progress: enrichmentProgress.value
    })

    // Calculate pagination
    booksTotalPages.value = Math.ceil(booksTotal.value / booksPerPage.value)
    hasNextPage.value = booksPage.value < booksTotalPages.value
    hasPrevPage.value = booksPage.value > 1

    status.value = `${booksTotal.value} books in this series (${editionMode})`
    booksLoading.value = false

    // Start progressive enrichment polling
    if (enrichmentStatus.value === 'pending' || enrichmentStatus.value === 'in_progress') {
      startEnrichmentPolling(seriesId)
    }
  } catch (error) {
    console.error('[SeriesView] Failed to toggle editions:', error)
    status.value = 'Failed to load editions'
    message.error('Failed to toggle editions. Please try again.')
  } finally {
    isTogglingEditions.value = false
  }
}

// Fetch audiobook metadata for all books in the series
async function fetchAudioMetadataForAll() {
  if (!detailItem.value || isFetchingAudioMeta.value) return

  isFetchingAudioMeta.value = true
  const seriesId = detailItem.value.series_id

  try {
    console.log(`[SeriesView] Fetching audiobook metadata for all books in series ${seriesId}`)

    const result = await api.fetchSeriesAudioMetadata(seriesId, null)

    console.log(`[SeriesView] Enriched ${result.enriched_count} books with audiobook metadata`)

    // Merge enriched audiobook data into existing books
    if (result.books && result.books.length > 0) {
      enrichedBooks.value = enrichedBooks.value.map(existingBook => {
        const enriched = result.books.find(b =>
          b.position === existingBook.position ||
          (b.display_title === existingBook.display_title && b.author === existingBook.author)
        )

        if (enriched) {
          // Merge audiobook metadata
          return {
            ...existingBook,
            has_audiobook: enriched.has_audiobook,
            audio_seconds: enriched.audio_seconds
          }
        }

        return existingBook
      })

      // Update cache with new audiobook metadata (use edition mode key)
      if (detailItem.value && detailItem.value.series_id) {
        const editionMode = showAllEditions.value ? 'all' : 'canonical'
        const cacheKey = `${detailItem.value.series_id}:${editionMode}`
        seriesCache.set(cacheKey, {
          books: enrichedBooks.value,
          total: booksTotal.value,
          enrichment_status: enrichmentStatus.value,
          enrichment_progress: enrichmentProgress.value
        })
      }
    }

    if (result.errors && result.errors.length > 0) {
      console.warn(`[SeriesView] ${result.errors.length} books failed to fetch audiobook metadata:`, result.errors)
    }

  } catch (err) {
    console.error('[SeriesView] Failed to fetch audiobook metadata:', err)
    status.value = `Failed to fetch audiobook metadata: ${err.message}`
  } finally {
    isFetchingAudioMeta.value = false
  }
}

// Cleanup polling on component unmount
onUnmounted(() => {
  pollIntervals.forEach(id => clearInterval(id))
  pollIntervals = []
})

// Load next page of books
function loadNextPage() {
  if (!hasNextPage.value || !detailItem.value) return

  booksPage.value++
  hasNextPage.value = booksPage.value < booksTotalPages.value
  hasPrevPage.value = booksPage.value > 1

  // Scroll to top of books grid
  if (detailElement.value?.$el) {
    detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Load previous page of books
function loadPrevPage() {
  if (!hasPrevPage.value || !detailItem.value) return

  booksPage.value--
  hasNextPage.value = booksPage.value < booksTotalPages.value
  hasPrevPage.value = booksPage.value > 1

  // Scroll to top of books grid
  if (detailElement.value?.$el) {
    detailElement.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Handle book card click - navigate to DiscoverView with detail view open
function handleBookClick(book) {
  const normalizedTitle = book.display_title.toLowerCase().replace(/ /g, '-').replace(/[^\w-]/g, '')
  router.push({
    name: 'discover',
    query: {
      q: book.display_title,
      view: 'cards',
      limit: '100',
      detail: normalizedTitle  // Open detail view immediately
    }
  })
}

// Close detail view
const closeDetail = (options = {}) => {
  const { suppressNavigation = false } = options
  currentDetailSeriesId.value = null  // Reset guard
  detailItem.value = null
  enrichedBooks.value = []
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
    detailItem.value = null
    enrichedBooks.value = []
  }
})
</script>

<style scoped>
.series-view {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
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

@media (max-width: 767px) {
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

/* Books Grid */
.books-grid {
  width: 100%;
}

/* Responsive - mobile breakpoint (0-767px) */
@media (max-width: 767px) {
  .search-input-item {
    min-width: 100%;
  }

  .books-grid {
    gap: 0.75rem !important;
  }
}
</style>
