<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :width="size"
    :height="size"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <!-- Clock circle -->
    <circle cx="12" cy="12" r="10" />

    <!-- Clock hands -->
    <path d="M12 6v6l4 2" />

    <!-- Upload arrow -->
    <path d="M12 2v2" />
    <path d="M9 3l3-1 3 1" />
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
