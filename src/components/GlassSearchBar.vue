<template>
  <n-input
    v-model:value="modelValue"
    :placeholder="placeholder"
    :size="size"
    class="glass-search-bar"
    clearable
    @keyup.enter="handleEnter"
    @update:value="handleUpdate"
    @clear="handleClear"
  >
    <template #prefix>
      <span class="search-icon">🔍</span>
    </template>
  </n-input>
</template>

<script setup>
import { computed } from 'vue'
import { NInput } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'

const props = defineProps({
  placeholder: {
    type: String,
    default: 'Search...'
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  }
})

const modelValue = defineModel()
const emit = defineEmits(['search', 'clear', 'update:modelValue'])

// Responsive breakpoints
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

const handleEnter = () => {
  emit('search', modelValue.value)
}

const handleUpdate = (value) => {
  emit('update:modelValue', value)
}

const handleClear = () => {
  emit('clear')
}
</script>

<style scoped>
.glass-search-bar {
  /* Glassmorphic input styling */
  background: rgba(42, 42, 42, 0.5) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

/* Shimmer effect on focus */
.glass-search-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.08),
    transparent
  );
  transition: left 0.5s ease;
  z-index: 0;
  pointer-events: none;
}

.glass-search-bar:focus-within::before {
  left: 100%;
}

.glass-search-bar:focus-within {
  border-color: rgba(80, 0, 0, 0.6) !important;
  box-shadow:
    0 0 0 3px rgba(80, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.glass-search-bar:hover:not(:focus-within) {
  background: rgba(42, 42, 42, 0.7) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
}

.search-icon {
  opacity: 0.5;
  font-size: 16px;
}

/* Responsive width - fills available space */
.glass-search-bar {
  width: 100%;
  min-width: 200px;
}

@media (max-width: 768px) {
  .glass-search-bar {
    min-width: 150px;
  }
}
</style>
