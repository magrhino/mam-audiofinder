<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NTabs, NTabPane, NSpin, NEmpty, NPagination, useMessage } from 'naive-ui'
import GlassSearchBar from '@/components/GlassSearchBar.vue'
import LibrarySelector from '@/components/LibrarySelector.vue'
import LibraryBookGrid from '@/components/LibraryBookGrid.vue'
import LibrarySeriesTable from '@/components/LibrarySeriesTable.vue'
import SeriesDiffModal from '@/components/SeriesDiffModal.vue'
import HardcoverLinkModal from '@/components/HardcoverLinkModal.vue'
import MissingBookSearchModal from '@/components/MissingBookSearchModal.vue'
import { useLibraryBooks } from '@/composables/useLibraryBooks'
import { useLibrarySeries } from '@/composables/useLibrarySeries'
import { useApi } from '@/composables/useApi'

const api = useApi()
const activeTab = ref('series')
const router = useRouter()
const message = useMessage()

// Libraries state
const libraries = ref([])
const librariesLoading = ref(false)
const selectedLibraryId = ref(null) // null = all libraries

onMounted(async () => {
  await fetchLibraries()
})

async function fetchLibraries() {
  librariesLoading.value = true
  try {
    const response = await api.get('/api/abs/libraries')
    if (response.ok) {
      libraries.value = response.libraries || []
    }
  } catch (e) {
    console.error('Failed to load libraries:', e)
  } finally {
    librariesLoading.value = false
  }
}

// Books tab state
const {
  libraryId: booksLibraryId,
  books,
  loading: booksLoading,
  error: booksError,
  searchQuery: booksQuery,
  page: booksPage,
  total: booksTotal,
  pages: booksPages,
  fetchBooks,
} = useLibraryBooks()

// Series tab state
const {
  libraryId: seriesLibraryId,
  series,
  loading: seriesLoading,
  error: seriesError,
  searchQuery: seriesQuery,
  page: seriesPage,
  total: seriesTotal,
  pages: seriesPages,
  fetchSeries,
} = useLibrarySeries()

// Sync library selection across both composables
watch(selectedLibraryId, (newId) => {
  booksLibraryId.value = newId
  seriesLibraryId.value = newId
})

// Diff modal state
const diffModalVisible = ref(false)
const diffSeriesName = ref('')
const diffHardcoverId = ref(null)

function openDiffModal(seriesName, hardcoverSeriesId = null) {
  diffSeriesName.value = seriesName
  diffHardcoverId.value = hardcoverSeriesId
  diffModalVisible.value = true
}

// Hardcover link modal state
const linkModalVisible = ref(false)
const linkModalSeries = ref(null)

function openLinkModal(seriesData) {
  linkModalSeries.value = seriesData
  linkModalVisible.value = true
}

// Missing book search modal state
const searchModalVisible = ref(false)
const searchModalBook = ref(null)
const searchModalSeriesName = ref('')

function handleLinkUpdated(linkInfo) {
  // Refresh series list to reflect new link status
  fetchSeries()
  message.success(`Updated Hardcover link for "${linkInfo.seriesName}"`)
}

// Handle refresh request from table
function handleRefresh(seriesData) {
  // Re-fetch series list
  fetchSeries()
  message.info(`Refreshing series data...`)
}

// Handle add to wishlist from popover
async function handleAddToWishlist(book) {
  try {
    const response = await api.post('/api/library/wishlist', {
      title: book.hardcover?.title || book.title,
      author: book.hardcover?.authors?.[0] || book.hardcover?.author_names?.[0],
      series_name: diffSeriesName.value || null,
      series_index: book.hardcover?.position,
      hardcover_book_id: book.hardcover?.book_id,
      cover_url: book.hardcover?.cover_url || book.hardcover?.image?.url,
    })

    if (response.ok !== false && response.id) {
      message.success(`Added "${book.hardcover?.title || book.title}" to wishlist`)
    } else {
      message.error('Failed to add to wishlist')
    }
  } catch (e) {
    console.error('Failed to add to wishlist:', e)
    message.error('Failed to add to wishlist')
  }
}

function handleBookClick(book) {
  const normalizedTitle = (book.title || '')
    .toLowerCase()
    .replace(/ /g, '-')
    .replace(/[^\w-]/g, '')

  router.push({
    name: 'discover',
    query: {
      q: book.title,
      view: 'cards',
      limit: '100',
      detail: normalizedTitle,
    },
  })
}

// Handle search for missing book from expanded series row
function handleMissingBookSearch(book) {
  // Open modal instead of navigating - preserves expanded row state
  searchModalBook.value = book
  // Series name is passed from ExpandedSeriesContent via _seriesName property
  searchModalSeriesName.value = book._seriesName || ''
  searchModalVisible.value = true
}

// Handle successful add from search modal
function handleModalTorrentAdded(result) {
  message.success(`Added "${result.title}" to qBittorrent`)
}
</script>

<template>
  <div class="library-view p-4 w-full max-w-full overflow-x-hidden">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold">Library</h1>
      <LibrarySelector
        v-model="selectedLibraryId"
        :libraries="libraries"
        :loading="librariesLoading"
      />
    </div>

    <NTabs v-model:value="activeTab" type="line" animated>
      <!-- Series Tab -->
      <NTabPane name="series" tab="Series">
        <GlassSearchBar
          v-model="seriesQuery"
          placeholder="Search series..."
          class="mb-4"
        />

        <div v-if="seriesError" class="text-red-500 mb-4 p-3 bg-red-900/20 rounded">
          {{ seriesError }}
        </div>

        <NSpin :show="seriesLoading">
          <NEmpty v-if="!seriesLoading && !seriesError && series.length === 0" description="No series found" />

          <LibrarySeriesTable
            v-else-if="series.length > 0"
            :series="series"
            @diff="openDiffModal"
            @editLink="openLinkModal"
            @refresh="handleRefresh"
            @addToWishlist="handleAddToWishlist"
            @search="handleMissingBookSearch"
          />

          <NPagination
            v-if="seriesPages > 1"
            v-model:page="seriesPage"
            :page-count="seriesPages"
            class="mt-4 flex justify-center"
          />
        </NSpin>
      </NTabPane>

      <!-- Books Tab -->
      <NTabPane name="books" tab="Books">
        <GlassSearchBar
          v-model="booksQuery"
          placeholder="Search books..."
          class="mb-4"
        />

        <div v-if="booksError" class="text-red-500 mb-4 p-3 bg-red-900/20 rounded">
          {{ booksError }}
        </div>

        <NSpin :show="booksLoading">
          <NEmpty v-if="!booksLoading && !booksError && books.length === 0" description="No books found" />

          <LibraryBookGrid
            v-else-if="books.length > 0"
            :books="books"
            @bookClick="handleBookClick"
          />

          <NPagination
            v-if="booksPages > 1"
            v-model:page="booksPage"
            :page-count="booksPages"
            class="mt-4 flex justify-center"
          />
        </NSpin>
      </NTabPane>
    </NTabs>

    <!-- Diff Modal -->
    <SeriesDiffModal
      v-model:show="diffModalVisible"
      :series-name="diffSeriesName"
      :hardcover-series-id="diffHardcoverId"
    />

    <!-- Hardcover Link Modal -->
    <HardcoverLinkModal
      v-model:show="linkModalVisible"
      :series="linkModalSeries"
      @linked="handleLinkUpdated"
    />

    <!-- Missing Book Search Modal -->
    <MissingBookSearchModal
      v-model:show="searchModalVisible"
      :book="searchModalBook"
      :series-name="searchModalSeriesName"
      @added="handleModalTorrentAdded"
    />
  </div>
</template>
