<template>
  <div class="series-view card">
    <div class="series-header">
      <h3>Series Discovery</h3>
      <div class="series-controls">
        <input v-model="form.title" type="text" placeholder="Book title..." style="width: 250px" @keyup.enter="runSearch">
        <input v-model="form.author" type="text" placeholder="Author (optional)" style="width: 200px" @keyup.enter="runSearch">
        <select v-model="form.limit">
          <option value="5">5 results</option>
          <option value="10">10 results</option>
          <option value="20">20 results</option>
          <option value="30">30 results</option>
          <option value="40">40 results</option>
          <option value="50">50 results</option>
        </select>
        <button class="primary" @click="runSearch">🔍 Search Series</button>
      </div>
    </div>
    <div class="muted" style="margin: 1rem 0;" v-text="status"></div>

    <div v-if="!detail">
      <SeriesTable :items="results" @select="loadDetail" />
    </div>

    <div v-else>
      <div style="margin: 1rem 0;">
        <button class="secondary" @click="detail = null">← Back to Series List</button>
      </div>
      <h3>{{ detail.series_name }}</h3>
      <div class="showcase-grid">
        <div class="showcase-card" v-for="book in detail.books" :key="book.book_id">
          <div class="showcase-title">{{ book.title }}</div>
          <div class="showcase-author">{{ book.author || book.author_name }}</div>
          <div class="muted">{{ book.release_year }} • {{ book.page_count || '?' }} pages</div>
          <div class="showcase-description">{{ book.description || 'No description available.' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SeriesTable from '@components/SeriesTable.vue'
import { useApi } from '@composables/useApi'

const api = useApi()
const route = useRoute()
const router = useRouter()
const form = reactive({ title: '', author: '', limit: '20' })
const status = ref('Search for a title to see matching series.')
const results = ref([])
const detail = ref(null)

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

  form.title = getValue('title', '')
  form.author = getValue('author', '')
  form.limit = getValue('limit', '20')
}

const runSearch = async () => {
  if (!form.title.trim()) {
    status.value = 'Please enter a book title.'
    results.value = []
    detail.value = null
    return
  }
  status.value = 'Searching for series…'
  detail.value = null
  try {
    const data = await api.searchSeries({
      title: form.title.trim(),
      author: form.author.trim(),
      limit: parseInt(form.limit, 10)
    })
    results.value = data.hardcover_series || []
    status.value = results.value.length ? `Found ${results.value.length} series` : 'No series found.'
    router.replace({
      query: normalizeQuery({
        title: form.title.trim(),
        author: form.author.trim(),
        limit: form.limit
      })
    })
  } catch (err) {
    status.value = `Series search failed: ${err.message}`
  }
}

const loadDetail = async (series) => {
  status.value = 'Loading series books…'
  try {
    const data = await api.getSeriesBooks(series.series_id)
    detail.value = data
    status.value = `${data.books?.length || 0} books in this series`
  } catch (err) {
    status.value = `Failed to load series: ${err.message}`
  }
}

onMounted(() => {
  syncForm()
  if (form.title) {
    runSearch()
  }
})

watch(() => [route.query.title, route.query.author, route.query.limit], () => {
  const previous = form.title
  syncForm()
  if (form.title && form.title !== previous) {
    runSearch()
  }
  if (!form.title) {
    results.value = []
    detail.value = null
    status.value = 'Please enter a book title.'
  }
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
