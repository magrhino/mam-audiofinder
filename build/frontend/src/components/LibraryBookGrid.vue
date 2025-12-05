<script setup>
import { NCard, NText, NImage } from 'naive-ui'

const props = defineProps({
  books: { type: Array, required: true },
})

const emit = defineEmits(['bookClick'])

const getCoverUrl = (book) => {
  // Use the cover proxy endpoint with the book's ABS item ID
  if (book.id) {
    return `/api/library/cover/${book.id}`
  }
  return null
}

const handleBookClick = (book) => {
  emit('bookClick', book)
}
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
    <NCard
      v-for="book in books"
      :key="book.id"
      class="glass-panel hover:glass-panel-hover cursor-pointer transition-all"
      :content-style="{ padding: '0.75rem' }"
      @click="handleBookClick(book)"
    >
      <div class="flex flex-col gap-2">
        <NImage
          v-if="getCoverUrl(book)"
          :src="getCoverUrl(book)"
          :alt="book.title"
          lazy
          object-fit="cover"
          class="w-full aspect-[2/3] rounded"
          :fallback-src="''"
        >
          <template #placeholder>
            <div class="cover-skeleton w-full aspect-[2/3] rounded"></div>
          </template>
        </NImage>
        <div v-else class="cover-placeholder w-full aspect-[2/3] rounded flex items-center justify-center">
          <span class="text-xs text-gray-500">No Cover</span>
        </div>
        <div class="flex flex-col gap-1">
          <NText class="text-sm font-semibold line-clamp-2" :title="book.title">
            {{ book.title }}
          </NText>
          <NText class="text-xs text-gray-400 line-clamp-1" v-if="book.author" :title="book.author">
            {{ book.author }}
          </NText>
          <NText class="text-xs text-gray-500" v-if="book.series_name">
            {{ book.series_name }}
            <span v-if="book.series_index"> #{{ book.series_index }}</span>
          </NText>
        </div>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
}

.cover-placeholder {
  background-color: #2a2a2a;
  border: 1px solid #3a3a3a;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
</style>
