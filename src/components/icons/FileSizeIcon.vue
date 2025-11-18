<template>
  <svg
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
  >
    <g>
      <path stroke-linecap="round" stroke-linejoin="round" d="m8.999 7.501l3 3l3-3m-3 3V.751m-3 18h-3.75" />
      <path d="M15.374 19.126a.375.375 0 0 1 0-.75m0 .75a.375.375 0 0 0 0-.75m3.75.75a.375.375 0 0 1 0-.75m0 .75a.375.375 0 0 0 0-.75" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M18.749 23.251h-13.5a4.5 4.5 0 0 1 0-9h13.5a4.5 4.5 0 1 1 0 9" />
    </g>
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
