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
        <option value="25">25</option>
        <option value="50">50</option>
        <option value="100">100</option>
      </select>
      <button type="submit">Search</button>
    </form>

    <div class="muted" v-text="status"></div>

    <div class="table-responsive" v-if="data.length">
      <n-data-table
        ref="tableRef"
        :columns="columns"
        :data="data"
        :pagination="pagination"
        :bordered="false"
        :loading="loading"
        :scroll-x="1200"
        striped
      />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NDataTable } from 'naive-ui'
import { useApi } from '@composables/useApi'
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'

const api = useApi()
const route = useRoute()
const router = useRouter()

// Initialize data table with search configuration
const {
  tableRef,
  data,
  columns,
  pagination,
  loading: tableLoading,
  setData,
  clearData,
  sort
} = useMAMSearchDataTable({
  viewType: 'search',
  defaultPageSize: 25,
  onAdd: addTorrent
})

const form = reactive({ q: '', sort: 'default', perpage: '25' })
const status = ref('')
const loading = ref(false)

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
  form.perpage = getValue('perpage', '25')
}

const runSearch = async (silent = false) => {
  if (!form.q.trim()) {
    status.value = 'Enter a search query to get started.'
    clearData()
    return
  }
  loading.value = true
  status.value = silent ? status.value : 'Searching…'
  clearData()

  try {
    const results = await api.search({
      tor: { text: form.q.trim(), sortType: form.sort },
      perpage: parseInt(form.perpage, 10)
    })
    setData(results.results || [])
    status.value = data.value.length ? `${data.value.length} results shown` : 'No results.'

    // Sync table pagination with form dropdown
    pagination.value.pageSize = parseInt(form.perpage, 10)

    // Apply default sort if specified
    if (form.sort === 'seedersDesc') {
      sort('seeders', 'descend')
    } else if (form.sort === 'dateDesc') {
      sort('added', 'descend')
    } else if (form.sort === 'sizeDesc') {
      sort('size', 'descend')
    }

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

async function addTorrent(rowState) {
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
    clearData()
    status.value = ''
  }
})
</script>

<style scoped>
/* Uses main.css styles */

.table-responsive {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
  margin-top: var(--spacing-md, 1rem);
}

/* Desktop: Full width, no constraints */
@media (min-width: 1024px) {
  .table-responsive {
    max-width: 100%;
  }
}

/* Tablet: Comfortable scrolling */
@media (min-width: 768px) and (max-width: 1023px) {
  .table-responsive {
    max-width: 100%;
    overflow-x: auto;
  }
}

/* Mobile: Optimized padding and scroll */
@media (max-width: 767px) {
  .table-responsive {
    margin-left: calc(-1 * var(--spacing-md, 1rem));
    margin-right: calc(-1 * var(--spacing-md, 1rem));
    padding: 0 var(--spacing-md, 1rem);
  }
}
</style>
