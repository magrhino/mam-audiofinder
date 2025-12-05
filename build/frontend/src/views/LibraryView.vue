<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NTabs, NTabPane, NSpin, NEmpty, NPagination } from 'naive-ui'
import GlassSearchBar from '@/components/GlassSearchBar.vue'
import SourceToggle from '@/components/SourceToggle.vue'
import LibraryBookGrid from '@/components/LibraryBookGrid.vue'
import LibrarySeriesTable from '@/components/LibrarySeriesTable.vue'
import SeriesDiffModal from '@/components/SeriesDiffModal.vue'
import { useLibraryBooks } from '@/composables/useLibraryBooks'
import { useLibrarySeries } from '@/composables/useLibrarySeries'
import { useApi } from '@/composables/useApi'

const api = useApi()
const activeTab = ref('series')
const router = useRouter()

// Config state
const config = ref({ abs_configured: false, hardcover_configured: false })

onMounted(async () => {
  try {
    const cfg = await api.get('/config')
    config.value = {
      abs_configured: !!cfg.abs_configured,
      hardcover_configured: !!cfg.hardcover_configured,
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
})

// Books tab state
const {
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
  series,
  loading: seriesLoading,
  error: seriesError,
  searchQuery: seriesQuery,
  page: seriesPage,
  total: seriesTotal,
  pages: seriesPages,
  source: seriesSource,
  fetchSeries,
} = useLibrarySeries()

// Diff modal state
const diffModalVisible = ref(false)
const diffSeriesName = ref('')
const diffHardcoverId = ref(null)

function openDiffModal(seriesName, hardcoverSeriesId = null) {
  diffSeriesName.value = seriesName
  diffHardcoverId.value = hardcoverSeriesId
  diffModalVisible.value = true
}

function handleBookClick(book) {
  const normalizedTitle = (book.title || '')
    .toLowerCase()
    .replace(/ /g, '-')
    .replace(/[^\w-]/g, '')

  router.push({
    name: 'showcase',
    query: {
      q: book.title,
      limit: '25',
      detail: normalizedTitle,
    },
  })
}
</script>

<template>
  <div class="library-view p-4 w-full max-w-full overflow-x-hidden">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold">Library</h1>
      <SourceToggle
        v-model="seriesSource"
        :abs-configured="config.abs_configured"
        :hardcover-configured="config.hardcover_configured"
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
  </div>
</template>
