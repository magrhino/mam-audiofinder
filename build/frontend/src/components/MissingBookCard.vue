<script setup>
import { computed } from 'vue'
import { NImage } from 'naive-ui'
import { useBreakpoints } from '@/composables/useBreakpoints'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['search'])

const { isMobile } = useBreakpoints()

// Extract book data from hardcover object
const title = computed(() => props.book.hardcover?.title || props.book.title || 'Unknown')
const author = computed(() => props.book.hardcover?.authors?.[0] || props.book.hardcover?.author_names?.[0] || '')
const position = computed(() => props.book.hardcover?.position)
const coverUrl = computed(() => props.book.hardcover?.cover_url || props.book.hardcover?.image?.url || '')

function handleClick() {
  emit('search', props.book)
}
</script>

<template>
  <div
    class="missing-book-card"
    :class="{ 'mobile-layout': isMobile }"
    @click="handleClick"
    role="button"
    tabindex="0"
    @keydown.enter="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- Hover glow effect -->
    <div class="card-glow"></div>

    <!-- Cover with overlay gradient -->
    <div class="card-cover">
      <div class="cover-inner">
        <NImage
          v-if="coverUrl"
          :src="coverUrl"
          :alt="title"
          :width="isMobile ? 44 : 52"
          :height="isMobile ? 66 : 78"
          object-fit="cover"
          lazy
          class="cover-image"
          :fallback-src="''"
        >
          <template #placeholder>
            <div class="cover-placeholder">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 6.253v11.495M17 9v6M7 9v6" stroke-linecap="round"/>
              </svg>
            </div>
          </template>
        </NImage>
        <div v-else class="cover-placeholder">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 6.253v11.495M17 9v6M7 9v6" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
      <!-- Cover shine effect -->
      <div class="cover-shine"></div>
    </div>

    <div class="card-info">
      <div class="card-title">{{ title }}</div>
      <div class="card-meta">
        <span v-if="position" class="card-position">#{{ position }}</span>
        <span v-if="author" class="card-author">{{ author }}</span>
      </div>
    </div>

    <!-- Action indicator -->
    <div class="card-action">
      <div class="action-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 21l-6-6m6 6v-4.5m0 4.5h-4.5" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="11" cy="11" r="8"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.missing-book-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  border-radius: 12px;
  background: rgba(36, 36, 36, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0;
  overflow: hidden;
}

/* Hover glow positioned behind content */
.card-glow {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0;
  background: radial-gradient(
    ellipse at center,
    rgba(80, 0, 0, 0.25) 0%,
    rgba(106, 0, 0, 0.15) 40%,
    transparent 70%
  );
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.missing-book-card:hover {
  background: rgba(50, 40, 40, 0.6);
  border-color: rgba(106, 0, 0, 0.4);
  transform: translateY(-3px);
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(106, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.missing-book-card:hover .card-glow {
  opacity: 1;
}

.missing-book-card:focus-visible {
  outline: 2px solid rgba(106, 0, 0, 0.7);
  outline-offset: 2px;
}

.missing-book-card:active {
  transform: translateY(-1px);
  transition-duration: 0.1s;
}

/* Mobile horizontal layout */
.missing-book-card.mobile-layout {
  flex-direction: row;
  align-items: center;
  padding: 12px;
  gap: 14px;
}

/* Cover container */
.card-cover {
  position: relative;
  flex-shrink: 0;
  z-index: 1;
}

.cover-inner {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.25),
    0 2px 4px rgba(0, 0, 0, 0.2);
}

.cover-image {
  display: block;
  border-radius: 6px;
}

.cover-placeholder {
  width: 52px;
  height: 78px;
  background: linear-gradient(
    145deg,
    rgba(60, 60, 60, 0.6) 0%,
    rgba(40, 40, 40, 0.8) 100%
  );
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.25);
}

.mobile-layout .cover-placeholder {
  width: 44px;
  height: 66px;
}

/* Cover shine effect */
.cover-shine {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.08) 0%,
    transparent 100%
  );
  border-radius: 6px 6px 0 0;
  pointer-events: none;
}

/* Info section */
.card-info {
  flex: 1;
  min-width: 0;
  text-align: center;
  z-index: 1;
}

.mobile-layout .card-info {
  text-align: left;
}

.card-title {
  font-weight: 500;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.95);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.35;
  letter-spacing: 0.01em;
  transition: color 0.2s ease;
}

.missing-book-card:hover .card-title {
  color: #fff;
}

.card-meta {
  font-size: 0.72rem;
  color: rgba(184, 184, 184, 0.8);
  margin-top: 5px;
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.mobile-layout .card-meta {
  justify-content: flex-start;
}

.card-position {
  color: rgba(220, 170, 80, 0.95);
  font-weight: 600;
  font-size: 0.75rem;
  background: rgba(220, 170, 80, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.02em;
}

.card-author {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
}

/* Action indicator */
.card-action {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transform: scale(0.8) translateX(4px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 2;
}

.mobile-layout .card-action {
  position: relative;
  top: auto;
  right: auto;
  opacity: 0.5;
  transform: none;
}

.action-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(106, 0, 0, 0.7);
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(80, 0, 0, 0.4);
  backdrop-filter: blur(4px);
}

.missing-book-card:hover .card-action {
  opacity: 1;
  transform: scale(1) translateX(0);
}

.mobile-layout:hover .card-action {
  opacity: 1;
}
</style>
