<template>
  <span
    id="navHealth"
    class="health-indicator"
    :class="healthClass"
    title="Application health status"
  >
    <span class="health-dot"></span>
    <span class="health-text">{{ healthText }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  health: {
    type: Object,
    required: true,
    validator: (value) => {
      return typeof value.ok === 'boolean' && typeof value.checking === 'boolean'
    }
  }
})

const healthClass = computed(() => {
  if (props.health.checking) return ''
  return props.health.ok ? 'ok' : 'error'
})

const healthText = computed(() => {
  if (props.health.checking) return 'Checking...'
  return props.health.ok ? 'OK' : 'Error'
})
</script>

<style scoped>
/* Component-specific styles if needed, otherwise uses main.css */
</style>
