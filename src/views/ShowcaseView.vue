<template>
  <div class="showcase-view card">
    <div class="showcase-header">
      <h3>Audiobook Showcase</h3>
      <div class="showcase-controls">
        <input v-model="form.q" type="text" placeholder="Search audiobooks..." style="width: 300px" @keyup.enter="runSearch">
        <select v-model="form.limit">
          <option value="50">50 results</option>
          <option value="100">100 results</option>
          <option value="200">200 results</option>
          <option value="500">500 results</option>
        </select>
        <button class="primary" @click="runSearch">🔍 Search</button>
      </div>
    </div>
    <div class="muted" style="margin: 1rem 0;" v-text="status"></div>
    <div class="showcase-grid">
      <ShowcaseCard v-for="group in groups" :key="group.mam_id" :group="group" @select="showDetail" />
    </div>
    <div class="showcase-detail" v-if="detailGroup">
      <div class="showcase-detail-header">
        <h3>{{ detailGroup.display_title }}</h3>
        <div class="muted">{{ detailGroup.author }}</div>
        <button class="secondary" @click="closeDetail">← Back to results</button>
      </div>
      <div class="showcase-detail-content">
        <div v-for="version in detailGroup.versions" :key="version.id" class="showcase-detail-row">
          <div>
            <strong>{{ version.release_name }}</strong>
            <div class="muted">{{ version.format }} • {{ version.bitrate }} • {{ version.length }}</div>
          </div>
          <div class="showcase-detail-actions">
            <a v-if="version.mam_url" :href="version.mam_url" target="_blank" rel="noopener">Open on MAM</a>
            <ActionButton label="Copy" variant="primary" @click.stop="copyVersion(version)" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ShowcaseCard from '@components/ShowcaseCard.vue'
import ActionButton from '@components/ActionButton.vue'
import { useApi } from '@composables/useApi'

const api = useApi()
const route = useRoute()
const router = useRouter()
const form = reactive({ q: '', limit: '100' })
const status = ref('Enter a search query to find audiobooks.')
const groups = ref([])
const detailGroup = ref(null)

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
  status.value = 'Loading audiobooks…'
  groups.value = []
  detailGroup.value = null
  try {
    const data = await api.getShowcase({ query: form.q.trim(), limit: parseInt(form.limit, 10) })
    groups.value = data.groups || []
    status.value = groups.value.length ? `Showing ${data.total_groups} titles (${data.total_results} versions)` : 'No audiobooks found.'
    router.replace({
      query: normalizeQuery({ q: form.q.trim(), limit: form.limit })
    })
  } catch (err) {
    status.value = `Failed to load showcase: ${err.message}`
  }
}

const showDetail = (group) => {
  console.log('showDetail called with:', group)
  detailGroup.value = group
}

const closeDetail = () => {
  detailGroup.value = null
}

const copyVersion = async (version) => {
  const text = `${version.release_name} — ${version.format} — ${version.length}`
  try {
    await navigator.clipboard?.writeText(text)
    status.value = 'Copied release info to clipboard'
  } catch {
    status.value = text
  }
}

onMounted(() => {
  syncForm()
  if (form.q) {
    runSearch()
  }
})

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
</script>

<style scoped>
/* Uses main.css styles */
</style>
