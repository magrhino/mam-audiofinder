<template>
  <svg
    viewBox="0 0 48 48"
    fill="none"
    stroke="currentColor"
    :width="size"
    :height="size"
    stroke-width="3"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <!-- Seedling -->
    <path d="M24 28v12" />
    <path d="M24 28c0-6-4-10-10-10-2 0-4 1-6 2 2 5 6 8 10 8" />
    <path d="M24 28c0-6 4-10 10-10 2 0 4 1 6 2-2 5-6 8-10 8" />

    <!-- Upload arrow -->
    <path d="M24 6v10" />
    <path d="M18 12l6-6 6 6" />
  </svg>
</template>

<script setup>
defineProps({
  size: { type: Number, default: 20 }
})
</script>

<style scoped>
svg {
  display: block;
}
</style>
