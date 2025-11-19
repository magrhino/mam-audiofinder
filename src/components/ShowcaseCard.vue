<template>
  <div class="showcase-card" @click="handleClick">
    <div class="showcase-versions-badge">{{ versionsLabel }}</div>
    <div class="showcase-cover-skeleton" v-if="loadingCover">
      <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
    </div>
    <div class="showcase-cover-wrapper" v-else>
      <img v-if="coverUrl" class="showcase-cover" :src="coverUrl" :alt="group.display_title" loading="lazy" />
      <div v-else class="showcase-cover-placeholder">📚</div>
      <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
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
import { useApi } from '@composables/useApi'

const props = defineProps({
  group: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['select'])

const api = useApi()
const coverUrl = ref('')
const loadingCover = ref(true)

const loadCover = async () => {
  loadingCover.value = true
  try {
    if (props.group.cover_url) {
      coverUrl.value = props.group.cover_url
    } else if (props.group.mam_id && props.group.display_title) {
      const data = await api.fetchCover({
        mam_id: props.group.mam_id,
        title: props.group.display_title,
        author: props.group.author || '',
        max_retries: '2'
      })
      coverUrl.value = data.cover_url || ''
    }
  } catch (err) {
    console.warn('Cover load failed', err)
  } finally {
    loadingCover.value = false
  }
}

onMounted(loadCover)

const versionsLabel = computed(() => {
  const total = props.group.total_versions || 0
  return `${total} version${total === 1 ? '' : 's'}`
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
