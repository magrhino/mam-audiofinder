<template>
  <tr>
    <td style="padding:0.25rem;">
      <n-image
        v-if="item.abs_cover_url"
        :src="item.abs_cover_url"
        alt="Cover"
        lazy
        :width="60"
        :height="90"
        object-fit="cover"
        :intersection-observer-options="{ rootMargin: '50px' }"
      >
        <template #placeholder>
          <div style="width: 60px; height: 90px; background: #2a2a2a; display: flex; align-items: center; justify-content: center; color: #888; font-size: 0.7em;">
            Loading...
          </div>
        </template>
      </n-image>
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
      <n-button
        type="success"
        :ghost="!showForm"
        round
        :loading="loading && showForm"
        @click="toggleForm"
      >
        {{ showForm ? '📋 Close' : '📥 Import' }}
      </n-button>
    </td>
    <td>
      <n-button
        type="info"
        ghost
        round
        :loading="verifyLoading"
        :disabled="!item.imported_at || verifyLoading"
        @click="verifyItem"
      >
        {{ verifyButtonLabel }}
      </n-button>
      <n-button
        v-if="libraryItemUrl"
        tag="a"
        :href="libraryItemUrl"
        target="_blank"
        type="warning"
        ghost
        round
        size="tiny"
        style="margin-left: 4px;"
      >
        📚 Library
      </n-button>
    </td>
    <td>
      <n-popconfirm
        positive-text="Yes, remove"
        negative-text="Cancel"
        @positive-click="removeItem"
      >
        <template #trigger>
          <n-button
            type="error"
            ghost
            round
            :loading="removeLoading"
          >
            🗑️ Remove
          </n-button>
        </template>
        Remove this history item?
      </n-popconfirm>
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
          <n-button
            type="success"
            round
            size="small"
            :loading="loading"
            :disabled="!canImport"
            @click="handleImport"
          >
            {{ buttonLabel }}
          </n-button>
          <n-button
            secondary
            round
            size="small"
            :disabled="!form.selectedHash"
            @click="toggleTree"
          >
            {{ toggleTreeLabel }}
          </n-button>
        </div>
        <!-- Persistent validation warnings (always visible when present) -->
        <div class="import-form__warnings" v-if="contextualMessage" style="color: #f39c12; padding: 0.5rem 0; white-space: pre-line; font-weight: 500;">
          {{ contextualMessage }}
        </div>
        <!-- Transient action feedback (loading, importing, etc.) -->
        <div class="import-form__status" v-if="statusMessage" style="padding: 0.5rem 0;">{{ statusMessage }}</div>
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
import { computed, ref, watch, onMounted } from 'vue'
import { NButton, NImage, NPopconfirm } from 'naive-ui'
import { useApi } from '@composables/useApi'
import { useImport } from '@composables/useImport'
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
const absBaseUrl = ref('')

// Load config to get ABS base URL
onMounted(async () => {
  try {
    const config = await api.getConfig()
    absBaseUrl.value = config.abs_base_url || ''
  } catch (err) {
    console.error('[HistoryRow] Failed to load config:', err)
  }
})

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

const libraryItemUrl = computed(() => {
  // Only show library link for mismatch status with ABS item ID
  if (props.item.abs_verify_status === 'mismatch' && props.item.abs_item_id && absBaseUrl.value) {
    return `${absBaseUrl.value}/item/${props.item.abs_item_id}`
  }
  return null
})
</script>

<style scoped>
.import-form {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.import-form__inputs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-sm);
  align-items: end;
}

.import-form__inputs label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.import-form__inputs input,
.import-form__inputs select {
  padding: 0.5rem;
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.import-form__inputs input:focus,
.import-form__inputs select:focus {
  outline: none;
  border-color: var(--input-focus);
  box-shadow: 0 0 0 3px rgba(139, 38, 53, 0.2);
}

.import-form__inline {
  display: flex;
  flex-direction: row !important;
  align-items: center;
  gap: 0.5rem;
}

.import-form__inline input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.import-form__status {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.import-form__warnings {
  color: #f39c12;
  padding: 0.5rem 0;
  white-space: pre-line;
  font-weight: 500;
}

.import-form__tree {
  max-height: 220px;
  overflow: auto;
  font-size: 0.85rem;
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--spacing-sm);
}

.import-form__tree ul {
  list-style: none;
  padding: 0;
  margin: 0;
  font-family: monospace;
}

.import-form__tree li {
  padding: 0.25rem 0;
  color: var(--text-secondary);
}
</style>
