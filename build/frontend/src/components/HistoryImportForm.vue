<template>
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
        strong
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
</template>

<script setup>
import { watch, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import { useImport } from '@composables/useImport'

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['updated', 'close'])

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

// Load form data on mount
onMounted(() => {
  loadFormData()
})

const handleImport = async () => {
  const result = await performImport()
  if (result.success) {
    emit('updated')
    emit('close')
  }
}
</script>

<style scoped>
.import-form {
  background: rgba(80, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(139, 38, 53, 0.3);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  box-shadow: 0 4px 12px rgba(80, 0, 0, 0.2);
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
