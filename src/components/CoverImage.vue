<template>
  <div class="cover-container" :style="{ position: 'relative', width: `${width}px`, height: `${height}px` }">
    <n-image
      v-if="localCoverUrl"
      :src="localCoverUrl"
      :width="width"
      :height="height"
      lazy
      :fallback-src="fallbackSrc"
      object-fit="cover"
      :intersection-observer-options="{
        rootMargin: '50px'
      }"
    >
      <template #placeholder>
        <div class="cover-skeleton" :style="{ width: `${width}px`, height: `${height}px` }">
          <div class="shimmer"></div>
        </div>
      </template>
    </n-image>

    <!-- Fallback for no cover -->
    <div v-else-if="error" class="cover-placeholder" :style="{ width: `${width}px`, height: `${height}px` }">
      <span class="cover-error">No Cover</span>
    </div>

    <!-- Loading state before fetch starts -->
    <div v-else class="cover-skeleton" :style="{ width: `${width}px`, height: `${height}px` }">
      <div class="shimmer"></div>
    </div>

    <!-- Library indicator -->
    <span
      v-if="inLibrary"
      class="in-library-indicator"
      title="Already in your library"
    >
      ✓
    </span>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { NImage } from 'naive-ui'
import { useCover } from '@composables/naive/useCover'

const props = defineProps({
  mamId: { type: String, required: true },
  title: { type: String, required: true },
  author: { type: String, default: '' },
  width: { type: Number, default: 60 },
  height: { type: Number, default: 80 },
  inLibrary: { type: Boolean, default: false },
  fallbackSrc: { type: String, default: '' }
})

const { coverUrl, error, fetchCover } = useCover({
  mamId: props.mamId,
  title: props.title,
  author: props.author
})

const localCoverUrl = ref('')

// Fetch cover on mount
onMounted(async () => {
  await fetchCover()
  if (coverUrl.value) {
    localCoverUrl.value = coverUrl.value
  }
})

// Watch for coverUrl changes
watch(coverUrl, (newUrl) => {
  if (newUrl) {
    localCoverUrl.value = newUrl
  }
})
</script>

<style scoped>
.cover-container {
  position: relative;
  display: inline-block;
}

.cover-skeleton {
  background: linear-gradient(
    90deg,
    rgba(40, 40, 40, 0.8) 0%,
    rgba(60, 60, 60, 0.8) 50%,
    rgba(40, 40, 40, 0.8) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shimmer {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.1) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.cover-placeholder {
  background-color: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  font-size: 10px;
}

.cover-error {
  text-align: center;
  padding: 0.25rem;
}

.in-library-indicator {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background-color: rgba(45, 122, 62, 0.95);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  z-index: 2;
}
</style>
