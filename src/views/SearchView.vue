<template>
  <div class="search-view">
    <form class="row" @submit.prevent="runSearch">
      <input v-model="form.q" type="text" placeholder="Search title/author/narrator" />
      <select v-model="form.sort">
        <option value="default">Sort: Default</option>
        <option value="seedersDesc">Seeders ↓</option>
        <option value="dateDesc">Date Added ↓</option>
        <option value="sizeDesc">Size ↓</option>
      </select>
      <select v-model="form.perpage">
        <option value="5">5</option>
        <option value="10">10</option>
        <option value="20">20</option>
        <option value="30">30</option>
        <option value="40">40</option>
        <option value="50">50</option>
      </select>
      <button type="submit">Search</button>
    </form>

    <div class="muted" v-text="status"></div>

    <table v-if="results.length">
      <thead>
        <tr>
          <th style="width: 80px">Cover</th>
          <th>Title</th>
          <th>Author</th>
          <th>Narrator</th>
          <th>Filetype</th>
          <th class="right">Size</th>
          <th class="right">Seeders</th>
          <th>Uploaded</th>
          <th class="center">Link</th>
          <th>Add</th>
        </tr>
      </thead>
      <tbody>
        <ResultRow
          v-for="(row, index) in resultsWithIds"
          :key="row.rowId"
          :item="row"
          :cover-loader="coverLoader"
          :row-id="row.rowId"
          @add="addTorrent"
        />
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ResultRow from '@components/ResultRow.vue'
import { useApi } from '@composables/useApi'
import { useCoverLoader, generateRowId } from '@composables/useCoverLoader'

const api = useApi()
const route = useRoute()
const router = useRouter()
const coverLoader = useCoverLoader()

const form = reactive({ q: '', sort: 'default', perpage: '20' })
const results = ref([])
const status = ref('')
const loading = ref(false)

// Add unique row IDs for key tracking
const resultsWithIds = computed(() =>
  results.value.map(row => ({
    ...row,
    rowId: `${row.id}-${row.added}-${generateRowId()}`
  }))
)

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
  form.sort = getValue('sort', 'default')
  form.perpage = getValue('perpage', '20')
}

const runSearch = async (silent = false) => {
  if (!form.q.trim()) {
    status.value = 'Enter a search query to get started.'
    results.value = []
    return
  }
  loading.value = true
  status.value = silent ? status.value : 'Searching…'
  results.value = []
  coverLoader.clearRowState()

  try {
    const data = await api.search({
      tor: { text: form.q.trim(), sortType: form.sort },
      perpage: parseInt(form.perpage, 10)
    })
    results.value = data.results || []
    status.value = results.value.length ? `${results.value.length} results shown` : 'No results.'

    router.replace({
      query: normalizeQuery({ q: form.q.trim(), sort: form.sort, perpage: form.perpage })
    })
  } catch (err) {
    console.error('Search failed', err)
    status.value = `Search failed: ${err.message}`
  } finally {
    loading.value = false
  }
}

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
    status.value = '✓ Added to qBittorrent'
    window.dispatchEvent(new CustomEvent('torrentAdded'))
  } catch (err) {
    status.value = `Add failed: ${err.message}`
  }
}

onMounted(() => {
  syncForm()
  if (form.q) {
    runSearch(true)
  }
})

watch(() => [route.query.q, route.query.sort, route.query.perpage], () => {
  const previousQuery = form.q
  syncForm()
  if (form.q && form.q !== previousQuery) {
    runSearch(true)
  }
  if (!form.q) {
    results.value = []
    status.value = ''
  }
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
