<template>
  <tr>
    <td style="padding:0.25rem;">
      <img v-if="item.abs_cover_url" :src="item.abs_cover_url" alt="Cover" loading="lazy" style="max-width:60px;max-height:90px;" />
      <span v-else class="muted" style="font-size:0.8em;">No cover</span>
    </td>
    <td>{{ item.title }}</td>
    <td>{{ item.author }}</td>
    <td>{{ item.narrator }}</td>
    <td class="center">
      <a v-if="detailUrl" :href="detailUrl" target="_blank" rel="noopener">🔗</a>
    </td>
    <td>{{ formattedWhen }}</td>
    <td>
      <StatusBadge :label="item.qb_status" :variant="statusVariant" :title="statusTooltip" />
      <span
        v-if="hasPathWarning"
        :title="item.path_warning"
        style="color: #e74c3c; cursor: help; margin-left: 4px; font-size: 1.1em;"
      >⚠️</span>
      <StatusBadge v-if="verifyBadge" :label="verifyBadge.label" :variant="verifyBadge.variant" :title="verifyBadge.title" />
    </td>
    <td>
      <ActionButton label="Import" variant="primary" :loading="loading && showForm" @click="toggleForm" />
    </td>
    <td>
      <ActionButton label="Verify" variant="secondary" :loading="verifyLoading" :disabled="!item.imported_at" @click="verifyItem" />
    </td>
    <td>
      <ActionButton label="Remove" variant="danger" :loading="removeLoading" @click="removeItem" />
    </td>
  </tr>
  <tr v-if="showForm">
    <td :colspan="columnCount">
      <div class="import-form">
        <div class="import-form__inputs">
          <label>
            Author
            <input v-model="form.author" type="text" />
          </label>
          <label>
            Title
            <input v-model="form.title" type="text" />
          </label>
          <label>
            Torrent
            <select v-model="form.selectedHash">
              <option value="" disabled>Select torrent…</option>
              <option v-for="torrent in torrents" :key="torrent.hash" :value="torrent.hash">
                {{ torrent.name }}
              </option>
            </select>
          </label>
          <label class="import-form__inline">
            <input type="checkbox" v-model="form.flatten" /> Flatten multi-disc
          </label>
          <ActionButton :label="buttonLabel" variant="success" :loading="loading" @click="performImport" />
          <ActionButton :label="toggleTreeLabel" variant="secondary" :disabled="!form.selectedHash" @click="loadTree" />
        </div>
        <div class="import-form__status" v-if="statusMessage">{{ statusMessage }}</div>
        <div class="import-form__tree" v-if="showTree">
          <ul>
            <li v-for="file in treeContents" :key="file.path">{{ file.path }} ({{ file.type }})</li>
          </ul>
        </div>
      </div>
    </td>
  </tr>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useApi } from '@composables/useApi'
import ActionButton from './ActionButton.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  columnCount: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits(['updated'])

const api = useApi()
const showForm = ref(false)
const loading = ref(false)
const verifyLoading = ref(false)
const removeLoading = ref(false)
const formLoaded = ref(false)
const torrents = ref([])
const torrentTree = ref(null)
const buttonLabel = ref('Copy to Library')
const form = reactive({
  author: props.item.author || '',
  title: props.item.title || '',
  selectedHash: props.item.qb_hash || '',
  flatten: false
})
const statusMessage = ref('')
const showTree = ref(false)

const loadFormData = async () => {
  if (formLoaded.value) return
  formLoaded.value = true
  loading.value = true
  try {
    const cfg = await api.getConfig()
    if (cfg.import_mode === 'link') {
      buttonLabel.value = 'Link to Library'
    } else if (cfg.import_mode === 'move') {
      buttonLabel.value = 'Move to Library'
    }
  } catch (err) {
    console.warn('Failed to fetch config', err)
  }

  try {
    const data = await api.getCompletedTorrents()
    torrents.value = data.items || []
    if (!form.selectedHash) {
      const match = torrents.value.find(t => t.hash === props.item.qb_hash || String(t.mam_id || '') === String(props.item.mam_id || ''))
      if (match) {
        form.selectedHash = match.hash
        statusMessage.value = '✓ Auto-selected matching torrent'
      }
    }
  } catch (err) {
    console.error('Failed to load torrents', err)
    statusMessage.value = 'Failed to load torrents'
  } finally {
    loading.value = false
  }
}

watch(showForm, (val) => {
  if (val) loadFormData()
})

const toggleForm = () => {
  showForm.value = !showForm.value
}

const performImport = async () => {
  if (!form.selectedHash) {
    statusMessage.value = 'Select a torrent to import'
    return
  }
  loading.value = true
  statusMessage.value = 'Importing…'
  try {
    const result = await api.importTorrent({
      author: form.author,
      title: form.title,
      hash: form.selectedHash,
      history_id: props.item.id,
      flatten: form.flatten
    })
    statusMessage.value = '✓ Import requested'
    showForm.value = false

    // Dispatch importCompleted event for live status updates
    window.dispatchEvent(new CustomEvent('importCompleted', {
      detail: {
        historyId: props.item.id,
        verification: result.verification
      }
    }))

    emit('updated')
  } catch (err) {
    statusMessage.value = `Import failed: ${err.message}`
  } finally {
    loading.value = false
  }
}

const verifyItem = async () => {
  verifyLoading.value = true
  try {
    await api.verifyHistoryItem(props.item.id)
    emit('updated')
  } catch (err) {
    statusMessage.value = `Verify failed: ${err.message}`
  } finally {
    verifyLoading.value = false
  }
}

const removeItem = async () => {
  if (!confirm('Remove this history item?')) return
  removeLoading.value = true
  try {
    await api.deleteHistoryItem(props.item.id)
    emit('updated')
  } catch (err) {
    statusMessage.value = `Remove failed: ${err.message}`
  } finally {
    removeLoading.value = false
  }
}

const loadTree = async () => {
  if (!form.selectedHash) return
  showTree.value = !showTree.value
  if (!showTree.value) return
  loading.value = true
  try {
    const data = await api.getTorrentTree(form.selectedHash)
    torrentTree.value = data
  } catch (err) {
    statusMessage.value = `Tree failed: ${err.message}`
    showTree.value = false
  } finally {
    loading.value = false
  }
}

const formattedWhen = computed(() => {
  if (!props.item.added_at) return ''
  return new Date(props.item.added_at.replace(' ', 'T') + 'Z').toLocaleString()
})

const statusVariant = computed(() => {
  const map = {
    grey: 'muted',
    blue: 'info',
    yellow: 'warning',
    green: 'success',
    red: 'danger'
  }
  return map[props.item.qb_status_color || 'grey'] || 'muted'
})

const statusTooltip = computed(() => props.item.path_warning || '')

const hasPathWarning = computed(() => !!props.item.path_warning)

const verifyBadge = computed(() => {
  if (!props.item.imported_at || !props.item.abs_verify_status) return null
  const note = props.item.abs_verify_note || ''
  if (props.item.abs_verify_status === 'verified') {
    return { label: 'Verified', variant: 'success', title: note }
  }
  if (props.item.abs_verify_status === 'mismatch') {
    return { label: 'Mismatch', variant: 'warning', title: note }
  }
  if (props.item.abs_verify_status === 'not_found') {
    return { label: 'Missing', variant: 'danger', title: note }
  }
  return { label: props.item.abs_verify_status, variant: 'muted', title: note }
})

const detailUrl = computed(() => props.item.mam_id ? `https://www.myanonamouse.net/t/${encodeURIComponent(props.item.mam_id)}` : '')

const toggleTreeLabel = computed(() => showTree.value ? 'Hide Files' : '📁 View Files')

const treeContents = computed(() => {
  if (!torrentTree.value?.files) return []
  return torrentTree.value.files
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
