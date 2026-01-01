<script setup>
import { ref, computed } from 'vue'
import { NPopover, NButton, NScrollbar, NImage, NSpin, NEmpty } from 'naive-ui'
import { useSeriesDiff } from '@/composables/useSeriesDiff'

const props = defineProps({
  count: {
    type: Number,
    default: 0,
  },
  seriesName: {
    type: String,
    required: true,
  },
  hardcoverSeriesId: {
    type: Number,
    default: null,
  },
})

const emit = defineEmits(['expand', 'addToWishlist'])

const popoverVisible = ref(false)
const hasLoaded = ref(false)

const {
  diffResult,
  loading,
  error,
  fetchDiff,
  addSelectedToWishlist,
} = useSeriesDiff()

// Load diff data when popover opens
async function handleShow() {
  popoverVisible.value = true
  if (!hasLoaded.value) {
    await fetchDiff(props.seriesName, props.hardcoverSeriesId)
    hasLoaded.value = true
  }
}

const missingBooks = computed(() => {
  return diffResult.value?.missing || []
})

async function handleAddToWishlist(book) {
  const bookId = book.hardcover?.book_id
  if (!bookId) return

  // Add single book to wishlist
  emit('addToWishlist', book)
}

function openFullModal() {
  popoverVisible.value = false
  emit('expand')
}

// Status indicator text
const statusText = computed(() => {
  if (props.count === 0) return '✓ Complete'
  return `⚠️ ${props.count} missing`
})

const statusClass = computed(() => {
  return props.count === 0 ? 'status-complete' : 'status-missing'
})
</script>

<template>
  <NPopover
    v-model:show="popoverVisible"
    trigger="click"
    placement="bottom-start"
    :width="380"
    @update:show="(val) => val && handleShow()"
  >
    <template #trigger>
      <span class="missing-indicator" :class="statusClass">
        {{ statusText }}
      </span>
    </template>

    <div class="missing-popover">
      <div class="popover-header">
        <span class="header-title">Missing from {{ seriesName }}</span>
        <NButton size="tiny" quaternary @click="openFullModal">
          Expand
        </NButton>
      </div>

      <NSpin :show="loading" size="small">
        <div v-if="error" class="popover-error">
          {{ error }}
        </div>

        <template v-else-if="missingBooks.length > 0">
          <NScrollbar style="max-height: 250px;">
            <div class="missing-list">
              <div
                v-for="item in missingBooks.slice(0, 5)"
                :key="item.hardcover?.book_id"
                class="missing-item"
              >
                <NImage
                  v-if="item.hardcover?.cover_url || item.hardcover?.image?.url"
                  :src="item.hardcover?.cover_url || item.hardcover?.image?.url"
                  :alt="item.hardcover?.title"
                  width="36"
                  height="54"
                  object-fit="cover"
                  lazy
                  class="mini-cover"
                  :fallback-src="''"
                >
                  <template #placeholder>
                    <div class="cover-placeholder"></div>
                  </template>
                </NImage>
                <div v-else class="cover-placeholder">
                  <span>?</span>
                </div>

                <div class="item-info">
                  <div class="item-title">{{ item.hardcover?.title }}</div>
                  <div class="item-meta">
                    <span v-if="item.hardcover?.position">#{{ item.hardcover.position }}</span>
                    <span v-if="item.hardcover?.authors?.[0]">
                      {{ item.hardcover?.authors?.[0] }}
                    </span>
                  </div>
                </div>

                <NButton
                  size="tiny"
                  quaternary
                  class="add-btn"
                  @click="handleAddToWishlist(item)"
                >
                  + Add
                </NButton>
              </div>
            </div>
          </NScrollbar>

          <div v-if="missingBooks.length > 5" class="more-indicator">
            + {{ missingBooks.length - 5 }} more...
          </div>
        </template>

        <NEmpty v-else-if="!loading" description="No missing books" size="small" />
      </NSpin>

      <div class="popover-footer">
        <NButton size="small" type="primary" @click="openFullModal">
          View All Details
        </NButton>
      </div>
    </div>
  </NPopover>
</template>

<style scoped>
.missing-indicator {
  cursor: pointer;
  font-size: 0.8rem;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.missing-indicator:hover {
  background: rgba(255, 255, 255, 0.1);
}

.status-complete {
  color: rgba(80, 180, 100, 0.9);
}

.status-missing {
  color: rgba(220, 180, 80, 0.9);
}

.missing-popover {
  padding: 8px 0;
}

.popover-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 8px;
}

.header-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.popover-error {
  color: rgba(220, 80, 80, 0.9);
  padding: 12px;
  text-align: center;
  font-size: 0.85rem;
}

.missing-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 12px;
}

.missing-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border-radius: 6px;
  transition: background 0.2s ease;
}

.missing-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.mini-cover {
  border-radius: 4px;
  flex-shrink: 0;
}

.cover-placeholder {
  width: 36px;
  height: 54px;
  background: rgba(80, 80, 80, 0.5);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 0.75rem;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-weight: 500;
  font-size: 0.85rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  font-size: 0.75rem;
  color: var(--text-subtle);
  display: flex;
  gap: 6px;
}

.add-btn {
  flex-shrink: 0;
}

.more-indicator {
  text-align: center;
  padding: 8px;
  font-size: 0.8rem;
  color: var(--text-subtle);
}

.popover-footer {
  padding: 8px 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}
</style>
