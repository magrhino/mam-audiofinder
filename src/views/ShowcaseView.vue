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

    <div v-if="!detailGroup" class="showcase-grid">
      <ShowcaseCard v-for="group in groups" :key="group.mam_id" :group="group" @select="showDetail" />
    </div>

    <div class="showcase-detail" v-if="detailGroup">
      <button class="showcase-detail-close" @click="closeDetail">✕ Close</button>

      <div class="showcase-detail-header">
        <!-- Cover -->
        <div v-if="detailGroup.mam_id" class="showcase-detail-cover">
          <img v-if="detailCoverUrl" :src="detailCoverUrl" :alt="detailGroup.display_title" loading="lazy" />
          <div v-else class="cover-skeleton">Loading cover...</div>
        </div>

        <!-- Info -->
        <div class="showcase-detail-info">
          <h2 class="showcase-detail-title">{{ detailGroup.display_title }}</h2>
          <div v-if="detailGroup.author" class="showcase-detail-author">by {{ detailGroup.author }}</div>
          <div v-if="detailGroup.narrator" class="showcase-detail-narrator">Narrated by {{ detailGroup.narrator }}</div>
          <div class="showcase-formats">
            <span v-for="format in detailGroup.formats || []" :key="format" class="showcase-format-badge">{{ format }}</span>
          </div>

          <!-- Description (if available) -->
          <div v-if="detailDescription" class="showcase-description">
            <div class="showcase-description-text" :class="{ collapsed: descriptionCollapsed }">
              {{ detailDescription }}
            </div>
            <button v-if="detailDescription.length > 200" class="description-toggle" @click.stop="descriptionCollapsed = !descriptionCollapsed">
              {{ descriptionCollapsed ? 'Show more' : 'Show less' }}
            </button>
            <div class="description-source muted">via Audiobookshelf</div>
          </div>
        </div>
      </div>

      <!-- Versions table -->
      <h3>Available Versions ({{ detailGroup.total_versions }})</h3>
      <table class="showcase-versions-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Format</th>
            <th class="right">Size</th>
            <th class="right">Seeders/Leechers</th>
            <th>Added</th>
            <th class="center">Link</th>
            <th>Add</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="version in detailGroup.versions" :key="version.id">
            <td>{{ version.title }}</td>
            <td>{{ version.format }}</td>
            <td class="right">{{ formatSize(version.size) }}</td>
            <td class="right">{{ version.seeders || 0 }} / {{ version.leechers || 0 }}</td>
            <td>{{ version.added }}</td>
            <td class="center">
              <a v-if="version.id" :href="`https://www.myanonamouse.net/t/${version.id}`" target="_blank" rel="noopener" title="Open on MAM">🔗</a>
            </td>
            <td>
              <ActionButton label="Add" variant="primary" @click.stop="addVersion(version)" />
            </td>
          </tr>
        </tbody>
      </table>
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
const detailCoverUrl = ref('')
const detailDescription = ref('')
const descriptionCollapsed = ref(true)

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

const showDetail = async (group) => {
  console.log('showDetail called with:', group)
  detailGroup.value = group
  detailCoverUrl.value = ''
  detailDescription.value = ''
  descriptionCollapsed.value = true

  // Load cover for detail view
  if (group.mam_id && group.display_title) {
    try {
      const data = await api.fetchCover({
        mam_id: group.mam_id,
        title: group.display_title,
        author: group.author || '',
        max_retries: '3'
      })
      detailCoverUrl.value = data.cover_url || ''

      // Also fetch description if available
      if (data.description) {
        detailDescription.value = data.description
      }
    } catch (err) {
      console.warn('Failed to load detail cover:', err)
    }
  }
}

const closeDetail = () => {
  detailGroup.value = null
  detailCoverUrl.value = ''
  detailDescription.value = ''
}

const formatSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

const addVersion = async (version) => {
  if (!version.dl || !version.id) {
    status.value = 'Cannot add: missing download link'
    return
  }

  try {
    await api.addTorrent({
      id: version.id,
      dl: version.dl,
      title: version.title,
      author: version.author_info,
      narrator: version.narrator_info
    })
    status.value = `✓ Added "${version.title}" to qBittorrent`

    // Dispatch event for history refresh
    window.dispatchEvent(new CustomEvent('torrentAdded', {
      detail: { item: version }
    }))
  } catch (err) {
    status.value = `Failed to add torrent: ${err.message}`
  }
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
