<template>
  <span class="status-badge" :class="`status-badge--${variant}`" :title="title">{{ label }}</span>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  variant: {
    type: String,
    default: 'muted'
  },
  title: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
