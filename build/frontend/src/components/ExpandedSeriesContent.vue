<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { NButton, NSpin, NSkeleton } from 'naive-ui'
import MissingBookCard from '@/components/MissingBookCard.vue'
import HardcoverLinkBadge from '@/components/HardcoverLinkBadge.vue'
import { useSeriesDiff } from '@/composables/useSeriesDiff'
import { useBreakpoints } from '@/composables/useBreakpoints'

const props = defineProps({
  seriesName: {
    type: String,
    required: true,
  },
  hardcoverSeriesId: {
    type: Number,
    default: null,
  },
  absBookCount: {
    type: Number,
    default: 0,
  },
  missingCount: {
    type: Number,
    default: 0,
  },
  hardcoverLinkConfidence: {
    type: Number,
    default: 0,
  },
  hardcoverSeriesName: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['search', 'viewDetails', 'editLink'])

const { isMobile, isTablet } = useBreakpoints()
const { diffResult, loading, error, fetchDiff } = useSeriesDiff()

const hasLoaded = ref(false)
const showAll = ref(false)

// Limit of books to show initially
const INITIAL_LIMIT = 6

// Get missing books from diff result
const missingBooks = computed(() => {
  return diffResult.value?.missing || []
})

// Books to display (limited or all)
const displayedBooks = computed(() => {
  if (showAll.value) {
    return missingBooks.value
  }
  return missingBooks.value.slice(0, INITIAL_LIMIT)
})

// Whether there are more books beyond the limit
const hasMore = computed(() => {
  return missingBooks.value.length > INITIAL_LIMIT
})

const remainingCount = computed(() => {
  return missingBooks.value.length - INITIAL_LIMIT
})

// Check if series is complete
const isComplete = computed(() => {
  if (loading.value) return false
  return missingBooks.value.length === 0
})

// Check if hardcover is linked
const isLinked = computed(() => {
  return !!props.hardcoverSeriesId
})

// Fetch diff data on mount
onMounted(async () => {
  if (props.hardcoverSeriesId) {
    await fetchDiff(props.seriesName, props.hardcoverSeriesId)
    hasLoaded.value = true
  }
})

// Re-fetch if hardcoverSeriesId changes
watch(() => props.hardcoverSeriesId, async (newId) => {
  if (newId && !hasLoaded.value) {
    await fetchDiff(props.seriesName, newId)
    hasLoaded.value = true
  }
})

function handleBookSearch(book) {
  // Include series name for modal context
  emit('search', { ...book, _seriesName: props.seriesName })
}

function handleViewDetails() {
  emit('viewDetails')
}

function handleShowAll() {
  showAll.value = true
}

function handleEditLink() {
  emit('editLink')
}
</script>

<template>
  <div class="expanded-series-content">
    <!-- Subtle gradient overlay -->
    <div class="content-gradient"></div>

    <!-- Header -->
    <div class="content-header">
      <div class="header-left">
        <span class="header-title">
          <svg class="title-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ seriesName }}
        </span>
        <span class="header-stats">
          <span class="stat-owned">{{ absBookCount }} in library</span>
          <template v-if="missingCount > 0">
            <span class="stat-divider">&bull;</span>
            <span class="stat-missing">{{ missingCount }} missing</span>
          </template>
        </span>
      </div>
      <div class="header-actions">
        <!-- Mobile: show Hardcover link status -->
        <HardcoverLinkBadge
          v-if="isMobile"
          :linked="isLinked"
          :confidence="hardcoverLinkConfidence"
          :series-name="hardcoverSeriesName"
          @edit="handleEditLink"
        />
        <NButton size="small" type="primary" @click="handleViewDetails" class="details-btn">
          <template #icon>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="15 3 21 3 21 9" stroke-linecap="round" stroke-linejoin="round"/>
              <line x1="10" y1="14" x2="21" y2="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </template>
          View Full Details
        </NButton>
      </div>
    </div>

    <!-- Content -->
    <div class="content-body">
      <!-- Not linked state -->
      <div v-if="!isLinked" class="state-card not-linked">
        <div class="state-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="state-content">
          <span class="state-title">Not linked to Hardcover</span>
          <span class="state-text">Link this series to see which books are missing from your library</span>
        </div>
        <NButton size="small" type="primary" ghost @click="handleEditLink">
          Link Series
        </NButton>
      </div>

      <!-- Loading state -->
      <div v-else-if="loading" class="loading-grid">
        <div
          v-for="i in (isMobile ? 2 : 3)"
          :key="i"
          class="skeleton-card"
          :class="{ 'mobile-layout': isMobile }"
          :style="{ animationDelay: `${i * 100}ms` }"
        >
          <div class="skeleton-cover">
            <NSkeleton :width="isMobile ? 44 : 52" :height="isMobile ? 66 : 78" />
          </div>
          <div class="skeleton-info">
            <NSkeleton text style="width: 80%;" />
            <NSkeleton text style="width: 50%; margin-top: 6px;" />
          </div>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="state-card error">
        <div class="state-icon error-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12" stroke-linecap="round"/>
            <line x1="12" y1="16" x2="12.01" y2="16" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="state-content">
          <span class="state-title error-text">Failed to load</span>
          <span class="state-text">{{ error }}</span>
        </div>
        <NButton size="small" quaternary @click="fetchDiff(seriesName, hardcoverSeriesId)">
          Retry
        </NButton>
      </div>

      <!-- Complete state -->
      <div v-else-if="isComplete" class="state-card complete">
        <div class="state-icon complete-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke-linecap="round" stroke-linejoin="round"/>
            <polyline points="22 4 12 14.01 9 11.01" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="state-content">
          <span class="state-title complete-text">Series complete!</span>
          <span class="state-text">All books from this series are in your library</span>
        </div>
      </div>

      <!-- Missing books grid -->
      <template v-else>
        <div class="missing-books-grid" :class="{ 'mobile-layout': isMobile, 'tablet-layout': isTablet && !isMobile }">
          <MissingBookCard
            v-for="(book, index) in displayedBooks"
            :key="book.hardcover?.book_id || book.title"
            :book="book"
            :style="{ animationDelay: `${index * 50}ms` }"
            @search="handleBookSearch"
          />
        </div>

        <!-- Show more button -->
        <div v-if="hasMore && !showAll" class="show-more">
          <button class="show-more-btn" @click="handleShowAll">
            <span class="btn-text">Show all {{ missingBooks.length }} missing books</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>

        <!-- Tip text -->
        <div class="tip-text">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="12" y1="17" x2="12.01" y2="17" stroke-linecap="round"/>
          </svg>
          <span>Click a book to search and add it to your library</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.expanded-series-content {
  position: relative;
  padding: 18px;
  background: rgba(26, 26, 26, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 12px;
  margin: 10px 4px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

/* Subtle gradient overlay for depth */
.content-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(80, 0, 0, 0.05) 0%,
    transparent 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
  pointer-events: none;
  z-index: 0;
}

/* Header */
.content-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  z-index: 1;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  font-size: 1rem;
  letter-spacing: 0.01em;
}

.title-icon {
  color: rgba(220, 170, 80, 0.8);
  flex-shrink: 0;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
}

.stat-owned {
  color: rgba(184, 184, 184, 0.9);
}

.stat-divider {
  color: rgba(255, 255, 255, 0.2);
}

.stat-missing {
  color: rgba(220, 170, 80, 0.9);
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.details-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Content body */
.content-body {
  position: relative;
  min-height: 100px;
  z-index: 1;
}

/* State cards (not-linked, error, complete) */
.state-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.1);
}

.state-icon {
  flex-shrink: 0;
  color: rgba(184, 184, 184, 0.5);
}

.state-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.state-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.9);
}

.state-text {
  font-size: 0.8rem;
  color: rgba(184, 184, 184, 0.7);
}

/* Complete state specific */
.state-card.complete {
  background: rgba(45, 122, 62, 0.08);
  border-color: rgba(45, 122, 62, 0.25);
  border-style: solid;
}

.complete-icon {
  color: rgba(80, 180, 100, 0.85);
}

.complete-text {
  color: rgba(80, 180, 100, 0.95);
}

/* Error state specific */
.state-card.error {
  background: rgba(170, 55, 55, 0.08);
  border-color: rgba(170, 55, 55, 0.25);
  border-style: solid;
}

.error-icon {
  color: rgba(220, 100, 100, 0.85);
}

.error-text {
  color: rgba(220, 100, 100, 0.95);
}

/* Loading skeleton */
.loading-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.skeleton-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  background: rgba(36, 36, 36, 0.4);
  border-radius: 12px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton-card.mobile-layout {
  flex-direction: row;
  gap: 14px;
}

.skeleton-cover {
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  width: 100%;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 0.3; }
}

/* Missing books grid */
.missing-books-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.missing-books-grid.tablet-layout {
  grid-template-columns: repeat(2, 1fr);
}

.missing-books-grid.mobile-layout {
  grid-template-columns: 1fr;
  gap: 10px;
}

/* Card entrance animation */
.missing-books-grid > * {
  animation: card-enter 0.3s ease-out backwards;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Show more button */
.show-more {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.show-more-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.show-more-btn:hover {
  background: rgba(106, 0, 0, 0.15);
  border-color: rgba(106, 0, 0, 0.35);
  color: rgba(255, 255, 255, 0.95);
}

.show-more-btn svg {
  transition: transform 0.2s ease;
}

.show-more-btn:hover svg {
  transform: translateY(2px);
}

/* Tip text */
.tip-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 0.75rem;
  color: rgba(184, 184, 184, 0.5);
}

.tip-text svg {
  opacity: 0.6;
}

/* Responsive */
@media (max-width: 767px) {
  .expanded-series-content {
    padding: 14px;
    margin: 8px 0;
  }

  .content-header {
    flex-direction: column;
    gap: 12px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .loading-grid {
    grid-template-columns: 1fr;
  }

  .state-card {
    flex-direction: column;
    text-align: center;
    padding: 20px 16px;
  }

  .state-content {
    align-items: center;
  }
}
</style>
