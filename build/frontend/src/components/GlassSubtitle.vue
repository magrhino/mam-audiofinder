<template>
  <n-gradient-text
    :size="size"
    class="glass-subtitle"
    :gradient="{
      deg: 135,
      from: 'rgba(216, 168, 168, 0.9)',
      to: 'rgba(120, 72, 72, 0.85)'
    }"
  >
    <slot></slot>
  </n-gradient-text>
</template>

<script setup>
import { computed } from 'vue'
import { NGradientText } from 'naive-ui'
import { useBreakpoints } from '@vueuse/core'

// Responsive breakpoints
const breakpoints = useBreakpoints({
  mobile: 0,
  tablet: 768,
  desktop: 1024
})

// Dynamic size based on screen size
const size = computed(() => {
  if (breakpoints.greater('desktop').value) {
    return 16 // Desktop: 16px
  } else if (breakpoints.greater('tablet').value) {
    return 14 // Tablet: 14px
  } else {
    return 13 // Mobile: 13px
  }
})
</script>

<style scoped>
.glass-subtitle {
  opacity: 0.9;
  text-align: center;
}
</style>
