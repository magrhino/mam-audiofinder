<template>
  <div class="showcase-card" @click="handleClick" :data-mam-id="group.mam_id">
    <!-- Version badge (hidden if hideVersionBadge prop is true OR only 1 version) -->
    <div v-if="!hideVersionBadge && (group.total_versions || 0) > 1" class="showcase-versions-badge">
      {{ versionsLabel }}
    </div>

    <!-- Skeleton/loading state (shown during enrichment or initial cover load) -->
    <div class="showcase-cover-skeleton" v-if="loadingCover || group.enrichment_pending">
      <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
      <span v-if="seriesNumber" class="series-number-badge" title="Series Number">{{ seriesNumber }}</span>
      <!-- Canonical edition badge (top-left) -->
      <span v-if="group.is_canonical === true" class="canonical-badge canonical-primary" title="Primary English Edition">📘 Primary</span>
      <span v-if="group.is_canonical === false" class="canonical-badge canonical-international" title="International Edition">🌐 Intl</span>
      <!-- Audiobook badges (only shown if metadata was fetched) -->
      <span v-if="group.has_audiobook === true" class="audiobook-available-badge" :title="`Audiobook available${audioDurationText}`">
        🎧{{ audioDurationText ? ' ' + audioDurationText : '' }}
      </span>
      <span v-if="group.has_audiobook === false" class="audiobook-unavailable-badge" title="No Audiobook Available">🚫 Audio</span>
    </div>

    <!-- Cover image (shown when loaded) -->
    <div class="showcase-cover-wrapper" v-else>
      <img v-if="coverUrl" class="showcase-cover" :src="coverUrl" :alt="group.display_title" loading="lazy" />
      <div v-else class="showcase-cover-placeholder">📚</div>
      <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
      <span v-if="seriesNumber" class="series-number-badge" title="Series Number">{{ seriesNumber }}</span>
      <!-- Canonical edition badge (top-left) -->
      <span v-if="group.is_canonical === true" class="canonical-badge canonical-primary" title="Primary English Edition">📘 Primary</span>
      <span v-if="group.is_canonical === false" class="canonical-badge canonical-international" title="International Edition">🌐 Intl</span>
      <!-- Audiobook badges (only shown if metadata was fetched) -->
      <span v-if="group.has_audiobook === true" class="audiobook-available-badge" :title="`Audiobook available${audioDurationText}`">
        🎧{{ audioDurationText ? ' ' + audioDurationText : '' }}
      </span>
      <span v-if="group.has_audiobook === false" class="audiobook-unavailable-badge" title="No Audiobook Available">🚫 Audio</span>
    </div>

    <div class="showcase-title">{{ group.display_title }}</div>
    <div class="showcase-author">{{ group.author }}</div>
    <div class="showcase-formats">
      <span v-for="format in group.formats || []" :key="format" class="showcase-format-badge">{{ format }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useCover } from '@composables/naive/useCover'

const props = defineProps({
  group: {
    type: Object,
    required: true
  },
  seriesNumber: {
    type: [String, Number],
    default: null
  },
  hideVersionBadge: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const cardElement = ref(null)

// Use enhanced useCover composable with lazy loading and passthrough support
const { coverUrl, loading: loadingCover, setupLazyLoad } = useCover({
  mamId: props.group.mam_id || '',
  title: props.group.display_title || '',
  author: props.group.author || '',
  initialUrl: props.group.cover_url || '',  // Backend passthrough (skips fetch)
  lazy: true,  // Enable lazy loading
  priority: 'normal',  // Standard 50px preload
  inLibrary: props.group.in_abs_library || false
})

// Setup lazy loading when card mounts
onMounted(() => {
  // Get the card element
  const element = document.querySelector(`.showcase-card[data-mam-id="${props.group.mam_id}"]`)
  if (element) {
    cardElement.value = element
    // Setup IntersectionObserver for lazy loading (unless cover already loaded from cache/passthrough)
    setupLazyLoad(element)
  }
})

const versionsLabel = computed(() => {
  const total = props.group.total_versions || 0
  return `${total} version${total === 1 ? '' : 's'}`
})

// Format audio duration from seconds to "Xh Ym" format
const audioDurationText = computed(() => {
  const seconds = props.group.audio_seconds
  if (!seconds || typeof seconds !== 'number') return ''

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  } else if (minutes > 0) {
    return `${minutes}m`
  }
  return ''
})

const handleClick = () => {
  console.log('ShowcaseCard clicked:', props.group)
  emit('select', props.group)
}
</script>

<style scoped>
/* Glassmorphic Showcase Card */
.showcase-card {
  background: rgba(36, 36, 36, 0.5);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: var(--spacing-md);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Shimmer effect on hover */
.showcase-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  transition: left 0.6s ease;
  z-index: 1;
}

.showcase-card:hover::before {
  left: 100%;
}

.showcase-card:hover {
  background: rgba(36, 36, 36, 0.7);
  border-color: rgba(80, 0, 0, 0.4);
  transform: translateY(-4px);
  box-shadow:
    0 8px 20px rgba(80, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Ensure content stays above shimmer */
.showcase-card > * {
  position: relative;
  z-index: 2;
}

/* Cover wrapper */
.showcase-cover-wrapper {
  width: 140px;
  height: 210px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.showcase-cover {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: var(--radius-md);
}

.showcase-cover-placeholder {
  width: 140px;
  height: 210px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  color: var(--text-subtle);
  font-size: 2rem;
  margin-bottom: var(--spacing-sm);
}

.showcase-cover-skeleton {
  width: 140px;
  height: 210px;
  background: linear-gradient(
    90deg,
    rgba(36, 36, 36, 0.5) 0%,
    rgba(42, 42, 42, 0.5) 50%,
    rgba(36, 36, 36, 0.5) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Title */
.showcase-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.95rem;
  margin-bottom: var(--spacing-xs);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* Author */
.showcase-author {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: var(--spacing-xs);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Format badges */
.showcase-formats {
  display: flex;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: var(--spacing-xs);
}

.showcase-format-badge {
  background: rgba(80, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  font-weight: 600;
  border: 1px solid rgba(106, 0, 0, 0.5);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Versions badge */
.showcase-versions-badge {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  background: rgba(106, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: white;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  pointer-events: none;
  border: 1px solid rgba(106, 0, 0, 0.6);
}

/* Library indicator */
.in-library-indicator {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: rgba(45, 122, 62, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  cursor: help;
  animation: fadeIn 0.3s ease-in;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.in-library-indicator:hover {
  background: rgba(45, 122, 62, 1);
  transform: scale(1.1);
  transition: all 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Series number badge (bottom-left) */
.series-number-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(80, 0, 0, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  min-width: 24px;
  height: 24px;
  padding: 0 6px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  cursor: help;
  animation: fadeIn 0.3s ease-in;
  border: 2px solid rgba(106, 0, 0, 0.6);
}

.series-number-badge:hover {
  background: rgba(106, 0, 0, 1);
  transform: scale(1.1);
  transition: all 0.2s ease;
}

/* Audiobook available badge (top-right of cover, green success) */
.audiobook-available-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0, 120, 0, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  padding: 3px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  cursor: help;
  animation: fadeIn 0.3s ease-in;
  border: 1px solid rgba(0, 180, 0, 0.8);
}

.audiobook-available-badge:hover {
  background: rgba(0, 150, 0, 1);
  transform: translateY(-2px);
  transition: all 0.2s ease;
}

/* Audiobook unavailable badge (top-right of cover, red warning) */
.audiobook-unavailable-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(180, 0, 0, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: white;
  padding: 3px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  cursor: help;
  animation: fadeIn 0.3s ease-in;
  border: 1px solid rgba(220, 0, 0, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.audiobook-unavailable-badge:hover {
  background: rgba(200, 0, 0, 1);
  transform: translateY(-2px);
  transition: all 0.2s ease;
}

/* Canonical edition badges (top-left of cover) */
.canonical-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  z-index: 10;
  cursor: help;
  animation: fadeIn 0.3s ease-in;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.canonical-primary {
  background: rgba(80, 0, 0, 0.95);
  color: white;
  border: 1px solid rgba(106, 0, 0, 0.8);
}

.canonical-primary:hover {
  background: rgba(106, 0, 0, 1);
  transform: translateY(-2px);
  transition: all 0.2s ease;
}

.canonical-international {
  background: rgba(100, 100, 100, 0.85);
  color: rgba(200, 200, 200, 1);
  border: 1px solid rgba(120, 120, 120, 0.7);
}

.canonical-international:hover {
  background: rgba(120, 120, 120, 0.95);
  transform: translateY(-2px);
  transition: all 0.2s ease;
}

/* Responsive */
@media (max-width: 768px) {
  .showcase-card {
    padding: var(--spacing-sm);
  }

  .showcase-cover-wrapper,
  .showcase-cover-placeholder,
  .showcase-cover-skeleton {
    width: 100%;
    height: auto;
    aspect-ratio: 2/3;
  }
}
</style>
