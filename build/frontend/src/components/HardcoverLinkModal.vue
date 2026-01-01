<script setup>
import { ref, watch, computed } from 'vue'
import {
  NModal,
  NInput,
  NButton,
  NSpin,
  NEmpty,
  NRadioGroup,
  NRadio,
  NScrollbar,
  NTag,
  useMessage,
} from 'naive-ui'
import { useHardcoverLink } from '@/composables/useHardcoverLink'

const props = defineProps({
  show: Boolean,
  series: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:show', 'linked'])

const message = useMessage()

const {
  loading,
  error,
  searchResults,
  currentLink,
  searchSeries,
  getLink,
  linkSeries,
  unlinkSeries,
  reset,
} = useHardcoverLink()

const searchQuery = ref('')
const selectedSeriesId = ref(null)
const searchTimeout = ref(null)

// Load current link when modal opens
watch(
  () => props.show,
  async (visible) => {
    if (visible && props.series) {
      reset()
      searchQuery.value = props.series.name || ''
      selectedSeriesId.value = props.series.hardcover_series_id || null

      // Get current link status
      await getLink(props.series.name)

      // If already linked, pre-select it
      if (currentLink.value?.linked) {
        selectedSeriesId.value = currentLink.value.hardcover_series_id
      }

      // Initial search
      await searchSeries(searchQuery.value)
    }
  }
)

// Debounced search
watch(searchQuery, (query) => {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    searchSeries(query)
  }, 300)
})

// Currently selected series from search results
const selectedSeries = computed(() => {
  if (!selectedSeriesId.value) return null
  return searchResults.value.find((s) => s.series_id === selectedSeriesId.value)
})

// Current link display info
const currentLinkInfo = computed(() => {
  if (!currentLink.value?.linked) return null
  return {
    name: currentLink.value.hardcover_series_name || 'Unknown Series',
    confidence: Math.round((currentLink.value.link_confidence || 0) * 100),
    linkedBy: currentLink.value.linked_by || 'unknown',
  }
})

async function handleConfirm() {
  if (!selectedSeries.value || !props.series) return

  const result = await linkSeries(props.series.name, selectedSeries.value)

  if (result.success) {
    message.success(`Linked to "${selectedSeries.value.series_name}"`)
    emit('linked', {
      seriesName: props.series.name,
      hardcoverSeriesId: selectedSeries.value.series_id,
      hardcoverSeriesName: selectedSeries.value.series_name,
    })
    close()
  } else {
    message.error(result.error || 'Failed to link series')
  }
}

async function handleUnlink() {
  if (!props.series) return

  const result = await unlinkSeries(props.series.name)

  if (result.success) {
    message.success('Series unlinked')
    selectedSeriesId.value = null
    emit('linked', {
      seriesName: props.series.name,
      hardcoverSeriesId: null,
    })
  } else {
    message.error(result.error || 'Failed to unlink series')
  }
}

function close() {
  emit('update:show', false)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    style="width: 550px; max-width: 95vw"
    title="Link to Hardcover Series"
    :mask-closable="true"
    @update:show="emit('update:show', $event)"
  >
    <div class="link-modal">
      <!-- Current Link Status -->
      <div v-if="currentLinkInfo" class="current-link">
        <div class="current-link-header">
          <span class="current-link-label">Currently Linked:</span>
          <NTag :type="currentLinkInfo.linkedBy === 'manual' ? 'success' : 'info'" size="small">
            {{ currentLinkInfo.linkedBy === 'manual' ? 'Manual' : 'Auto' }}
            ({{ currentLinkInfo.confidence }}%)
          </NTag>
        </div>
        <div class="current-link-name">{{ currentLinkInfo.name }}</div>
        <NButton size="small" type="error" quaternary @click="handleUnlink">
          Remove Link
        </NButton>
      </div>

      <!-- Search Input -->
      <div class="search-section">
        <NInput
          v-model:value="searchQuery"
          placeholder="Search Hardcover series..."
          clearable
          :loading="loading"
        >
          <template #prefix>
            <span>🔍</span>
          </template>
        </NInput>
      </div>

      <!-- Search Results -->
      <NSpin :show="loading" size="small">
        <div v-if="error" class="search-error">
          {{ error }}
        </div>

        <template v-else-if="searchResults.length > 0">
          <NScrollbar style="max-height: 300px">
            <NRadioGroup v-model:value="selectedSeriesId" class="results-list">
              <div
                v-for="result in searchResults"
                :key="result.series_id"
                class="result-item"
                :class="{ selected: selectedSeriesId === result.series_id }"
              >
                <NRadio :value="result.series_id" class="result-radio">
                  <div class="result-content">
                    <div class="result-name">{{ result.series_name }}</div>
                    <div class="result-meta">
                      <span v-if="result.author_name">{{ result.author_name }}</span>
                      <span>{{ result.book_count }} books</span>
                      <span v-if="result.readers_count">
                        {{ result.readers_count.toLocaleString() }} readers
                      </span>
                    </div>
                    <div v-if="result.books?.length" class="result-books">
                      {{ result.books.slice(0, 3).join(', ') }}
                      <span v-if="result.books.length > 3">...</span>
                    </div>
                  </div>
                </NRadio>
              </div>
            </NRadioGroup>
          </NScrollbar>
        </template>

        <NEmpty
          v-else-if="searchQuery && !loading"
          description="No series found"
          size="small"
        />
      </NSpin>

      <!-- Actions -->
      <div class="modal-actions">
        <NButton @click="close">Cancel</NButton>
        <NButton
          type="primary"
          :disabled="!selectedSeriesId || loading"
          @click="handleConfirm"
        >
          Confirm Selection
        </NButton>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.link-modal {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.current-link {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
}

.current-link-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.current-link-label {
  font-size: 0.85rem;
  color: var(--text-subtle);
}

.current-link-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.search-section {
  margin-top: 8px;
}

.search-error {
  color: rgba(220, 80, 80, 0.9);
  padding: 12px;
  text-align: center;
  font-size: 0.9rem;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}

.result-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s ease;
}

.result-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
}

.result-item.selected {
  background: rgba(80, 0, 0, 0.2);
  border-color: rgba(80, 0, 0, 0.5);
}

.result-radio {
  width: 100%;
}

.result-content {
  margin-left: 8px;
}

.result-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.result-meta {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
  color: var(--text-subtle);
  margin-bottom: 4px;
}

.result-books {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-style: italic;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
