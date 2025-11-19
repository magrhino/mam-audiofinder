<template>
  <n-gradient-text
    :size="size"
    :tag="tag"
    class="glass-title"
    :gradient="{
      deg: 135,
      from: 'rgb(210, 158, 158)',
      to: 'rgb(126, 63, 63)'
    }"
  >
    <slot></slot>
  </n-gradient-text>
</template>

<script setup>
import { computed } from 'vue'
import { NGradientText } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'

const props = defineProps({
  tag: {
    type: String,
    default: 'h1',
    validator: (value) => ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(value)
  }
})

// Responsive breakpoints
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic size based on screen size
const size = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 48 // Desktop: 48px
  } else if (breakpoints.greater('tablet').value) {
    return 36 // Tablet: 36px
  } else {
    return 28 // Mobile: 28px
  }
})
</script>

<style scoped>
.glass-title {
  font-weight: 700;
  margin-bottom: var(--spacing-sm, 0.5rem);
  text-align: center;
}
</style>
