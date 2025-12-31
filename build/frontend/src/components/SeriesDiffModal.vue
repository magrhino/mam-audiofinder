<script setup>
import { watch } from 'vue'
import { NModal, NSpin, NEmpty, NCheckbox, NButton, NTag, NScrollbar, NImage, useMessage } from 'naive-ui'
import { useSeriesDiff } from '@/composables/useSeriesDiff'

const props = defineProps({
  show: Boolean,
  seriesName: { type: String, required: true },
  hardcoverSeriesId: { type: Number, default: null },
})

const emit = defineEmits(['update:show'])

const message = useMessage()

const {
  diffResult,
  loading,
  error,
  selectedMissing,
  fetchDiff,
  toggleSelection,
  selectAll,
  clearSelection,
  addSelectedToWishlist,
} = useSeriesDiff()

watch(() => props.show, (visible) => {
  if (visible && props.seriesName) {
    fetchDiff(props.seriesName, props.hardcoverSeriesId)
  }
})

async function handleAddToWishlist() {
  const results = await addSelectedToWishlist()
  const success = results.filter(r => r.success).length
  if (success > 0) {
    message.success(`Added ${success} book${success > 1 ? 's' : ''} to wishlist`)
    clearSelection()
  }
  const failed = results.filter(r => !r.success).length
  if (failed > 0) {
    message.error(`Failed to add ${failed} book${failed > 1 ? 's' : ''}`)
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
    style="width: 800px; max-width: 95vw;"
    title="Series Comparison"
    :mask-closable="true"
    @update:show="emit('update:show', $event)"
  >
    <NSpin :show="loading">
      <div v-if="error" class="text-red-500 mb-4">{{ error }}</div>

      <template v-else-if="diffResult">
        <div class="mb-4 flex gap-4 text-sm">
          <span>📚 ABS: {{ diffResult.abs_book_count }}</span>
          <span>📖 Hardcover: {{ diffResult.hardcover_book_count }}</span>
          <span>✅ Match: {{ (diffResult.match_confidence * 100).toFixed(0) }}%</span>
        </div>

        <!-- Present Books -->
        <details v-if="diffResult.present.length" class="mb-4">
          <summary class="cursor-pointer font-semibold text-green-400">
            ✅ Present ({{ diffResult.present.length }})
          </summary>
          <div class="grid grid-cols-1 gap-2 mt-2 pl-4">
            <div v-for="item in diffResult.present" :key="item.hardcover?.book_id" class="flex items-center gap-2">
              <NTag type="success" size="small">In Library</NTag>
              <span>{{ item.hardcover?.title }}</span>
            </div>
          </div>
        </details>

        <!-- Missing Books -->
        <div v-if="diffResult.missing.length" class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-semibold text-yellow-400">⚠️ Missing ({{ diffResult.missing.length }})</span>
            <div class="flex gap-2">
              <NButton size="tiny" @click="selectAll">Select All</NButton>
              <NButton size="tiny" @click="clearSelection">Clear</NButton>
            </div>
          </div>
          <NScrollbar style="max-height: 300px;">
            <div class="grid grid-cols-1 gap-2">
              <div
                v-for="item in diffResult.missing"
                :key="item.hardcover?.book_id"
                class="flex items-center gap-3 p-2 rounded hover:bg-white/5"
              >
                <NCheckbox
                  :checked="selectedMissing.has(item.hardcover?.book_id)"
                  @update:checked="toggleSelection(item.hardcover?.book_id)"
                />
                <NImage
                  v-if="item.hardcover?.cover_url || item.hardcover?.image?.url"
                  :src="item.hardcover?.cover_url || item.hardcover?.image?.url"
                  :alt="item.hardcover?.title"
                  width="40"
                  height="56"
                  object-fit="cover"
                  lazy
                  class="rounded"
                  :fallback-src="''"
                >
                  <template #placeholder>
                    <div class="w-10 h-14 bg-gray-700 rounded animate-pulse"></div>
                  </template>
                </NImage>
                <div v-else class="w-10 h-14 bg-gray-700 rounded flex items-center justify-center">
                  <span class="text-xs text-gray-500">?</span>
                </div>
                <div class="flex-1">
                  <div class="font-medium">{{ item.hardcover?.title }}</div>
                  <div class="text-sm text-gray-400">
                    {{ item.hardcover?.authors?.[0] || item.hardcover?.author_names?.[0] }}
                    <span v-if="item.hardcover?.position"> • #{{ item.hardcover.position }}</span>
                  </div>
                </div>
              </div>
            </div>
          </NScrollbar>
        </div>

        <!-- Uncertain Matches -->
        <details v-if="diffResult.uncertain.length" class="mb-4">
          <summary class="cursor-pointer font-semibold text-orange-400">
            ❓ Uncertain ({{ diffResult.uncertain.length }})
          </summary>
          <div class="grid grid-cols-1 gap-2 mt-2 pl-4">
            <div v-for="item in diffResult.uncertain" :key="item.hardcover?.book_id">
              <span>{{ item.hardcover?.title }}</span>
              <span class="text-gray-400 text-sm"> (score: {{ item.score }})</span>
            </div>
          </div>
        </details>

        <!-- Actions -->
        <div class="flex justify-end gap-2 mt-4 pt-4 border-t border-white/10">
          <NButton @click="close">Close</NButton>
          <NButton
            type="primary"
            :disabled="selectedMissing.size === 0"
            @click="handleAddToWishlist"
          >
            Add {{ selectedMissing.size }} to Wishlist
          </NButton>
        </div>
      </template>

      <NEmpty v-else description="No comparison data" />
    </NSpin>
  </NModal>
</template>
