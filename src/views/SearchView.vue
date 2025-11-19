<template>
  <div class="search-view">
    <n-space :size="12" :wrap="true" align="end" class="search-form">
      <div class="search-input-wrapper">
        <GlassSearchBar
          v-model="form.q"
          placeholder="Search title/author/narrator"
          @search="runSearch"
        />
      </div>

      <GlassSelect
        v-model="form.sort"
        :options="sortOptions"
        width="160px"
      />

      <GlassSelect
        v-model="form.perpage"
        :options="perpageOptions"
        width="100px"
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

    <div class="muted" v-text="status"></div>

    <div class="glass-table-wrapper" v-if="data.length">
      <n-data-table
        ref="tableRef"
        :columns="columns"
        :data="data"
        :pagination="pagination"
        :bordered="false"
        :loading="loading"
        :scroll-x="scrollX"
        striped
      />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBreakpoints } from '@vueuse/core'
import { NDataTable, NSpace, NButton } from 'naive-ui'
import { useApi } from '@composables/useApi'
import { useMAMSearchDataTable } from '@composables/naive/useMAMSearchDataTable'
import GlassSearchBar from '@components/GlassSearchBar.vue'
import GlassSelect from '@components/GlassSelect.vue'

const api = useApi()
const route = useRoute()
const router = useRouter()

// Responsive breakpoints for dynamic scroll-x
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic scroll-x based on screen size
const scrollX = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 1400 // Desktop: More space for expanded columns
  } else if (breakpoints.greater('tablet').value) {
    return 1200 // Tablet: Standard layout
  } else {
    return 900 // Mobile: Compact layout
  }
})

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

// Dropdown options
const sortOptions = [
  { label: 'Sort: Default', value: 'default' },
  { label: 'Seeders ↓', value: 'seedersDesc' },
  { label: 'Date Added ↓', value: 'dateDesc' },
  { label: 'Size ↓', value: 'sizeDesc' }
]

const perpageOptions = [
  { label: '25', value: '25' },
  { label: '50', value: '50' },
  { label: '100', value: '100' }
]

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
/* Search form spacing */
.search-form {
  margin-bottom: var(--spacing-md, 1rem);
}

.search-input-wrapper {
  flex: 1;
  min-width: 200px;
}

/* Glass table wrapper applied via global .glass-table-wrapper class */

/* Mobile: Optimized padding */
@media (max-width: 767px) {
  .glass-table-wrapper {
    margin-left: calc(-1 * var(--spacing-md, 1rem));
    margin-right: calc(-1 * var(--spacing-md, 1rem));
  }

  .search-input-wrapper {
    min-width: 150px;
    width: 100%;
  }
}
</style>
