<template>
  <n-select
    v-model:value="modelValue"
    :options="options"
    :placeholder="placeholder"
    :size="size"
    :style="{ width: computedWidth }"
    class="glass-select"
    @update:value="handleUpdate"
  />
</template>

<script setup>
import { computed } from 'vue'
import { NSelect } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'

const props = defineProps({
  options: {
    type: Array,
    required: true
  },
  placeholder: {
    type: String,
    default: 'Select...'
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  width: {
    type: String,
    default: 'auto' // Can be '140px', '100%', 'auto', etc.
  }
})

const modelValue = defineModel()
const emit = defineEmits(['update:modelValue'])

// Responsive breakpoints
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Computed width based on screen size
const computedWidth = computed(() => {
  if (props.width !== 'auto') {
    return props.width
  }

  // Auto-size based on breakpoints
  if (breakpoints.greater('desktop').value) {
    return '160px'
  } else if (breakpoints.greater('tablet').value) {
    return '140px'
  } else {
    return '120px'
  }
})

const handleUpdate = (value) => {
  emit('update:modelValue', value)
}
</script>

<style scoped>
/* Glassmorphic select styling via :deep() */
:deep(.n-base-selection) {
  background: rgba(42, 42, 42, 0.5) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px !important;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

:deep(.n-base-selection:hover) {
  background: rgba(42, 42, 42, 0.7) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
}

:deep(.n-base-selection.n-base-selection--active),
:deep(.n-base-selection:focus-within) {
  border-color: rgba(80, 0, 0, 0.6) !important;
  box-shadow:
    0 0 0 3px rgba(80, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Shimmer effect - applied to parent */
.glass-select {
  position: relative;
}

.glass-select::before {
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
  z-index: 1;
  pointer-events: none;
  border-radius: 8px;
}

.glass-select:focus-within::before {
  left: 100%;
}

/* Dropdown menu styling */
:deep(.n-base-select-menu) {
  background: rgba(42, 42, 42, 0.95) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

:deep(.n-base-select-option) {
  transition: all 0.2s ease;
}

:deep(.n-base-select-option:hover) {
  background: rgba(80, 0, 0, 0.2) !important;
}

:deep(.n-base-select-option.n-base-select-option--selected) {
  background: rgba(80, 0, 0, 0.4) !important;
}
</style>
