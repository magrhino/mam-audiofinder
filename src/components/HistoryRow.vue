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
      <ActionButton :label="verifyButtonLabel" variant="secondary" :loading="verifyLoading" :disabled="!item.imported_at || verifyLoading" @click="verifyItem" />
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
          <ActionButton :label="buttonLabel" variant="success" :loading="loading" :disabled="!canImport" @click="handleImport" />
          <ActionButton :label="toggleTreeLabel" variant="secondary" :disabled="!form.selectedHash" @click="toggleTree" />
        </div>
        <div class="import-form__status" v-if="statusMessage">{{ statusMessage }}</div>
        <div class="import-form__context" v-if="contextualMessage && !statusMessage" style="color: #f39c12; padding: 0.5rem 0;">
          {{ contextualMessage }}
        </div>
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
import { computed, ref, watch } from 'vue'
import { useApi } from '@composables/useApi'
import { useImport } from '@composables/useImport'
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
const verifyLoading = ref(false)
const verifyButtonLabel = ref('🔄 Verify')
const removeLoading = ref(false)

// Use import composable for all import workflow
const {
  loading,
  torrents,
  statusMessage,
  buttonLabel,
  showTree,
  form,
  selectedTorrent,
  hasMultiDisc,
  canImport,
  treeContents,
  toggleTreeLabel,
  contextualMessage,
  loadFormData,
  performImport,
  toggleTree
} = useImport(props.item)

// Watch showForm to lazy-load form data
watch(showForm, (val) => {
  if (val) loadFormData()
})

const toggleForm = () => {
  showForm.value = !showForm.value
}

const handleImport = async () => {
  const result = await performImport()
  if (result.success) {
    showForm.value = false
    emit('updated')
  }
}

const verifyItem = async () => {
  const originalLabel = verifyButtonLabel.value
  verifyLoading.value = true
  verifyButtonLabel.value = '⏳ Verifying...'

  try {
    const result = await api.verifyHistoryItem(props.item.id)

    if (result.ok) {
      verifyButtonLabel.value = '✓ Done'
      // Trigger parent reload to get updated verification badge
      emit('updated')

      // Reset button after 2 seconds
      setTimeout(() => {
        verifyButtonLabel.value = originalLabel
        verifyLoading.value = false
      }, 2000)
    } else {
      verifyButtonLabel.value = '✗ Failed'
      // Reset button after 2 seconds
      setTimeout(() => {
        verifyButtonLabel.value = originalLabel
        verifyLoading.value = false
      }, 2000)
    }
  } catch (err) {
    console.error('[HistoryRow] Verify failed:', err)
    verifyButtonLabel.value = '✗ Error'

    // Reset button after 2 seconds
    setTimeout(() => {
      verifyButtonLabel.value = originalLabel
      verifyLoading.value = false
    }, 2000)
  }
}

const removeItem = async () => {
  if (!confirm('Remove this history item?')) return
  removeLoading.value = true
  try {
    await api.deleteHistoryItem(props.item.id)
    emit('updated')
  } catch (err) {
    console.error('[HistoryRow] Remove failed:', err)
  } finally {
    removeLoading.value = false
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
</script>

<style scoped>
/* Uses main.css styles */
</style>
