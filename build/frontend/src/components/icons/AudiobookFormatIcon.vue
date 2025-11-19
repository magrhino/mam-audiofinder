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
    <!-- Book body -->
    <path d="M10 8v30c0 2 1.5 4 4 4h20c2.5 0 4-2 4-4V14l-8-6H14c-2.5 0-4 2-4 4z"/>
    <path d="M38 14H30V8"/>

    <!-- Audio waves -->
    <path d="M18 22v8" />
    <path d="M22 20v12" />
    <path d="M26 24v6" />
    <path d="M30 18v16" />
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
