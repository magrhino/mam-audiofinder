<template>
  <button :class="classes" :disabled="disabled || loading" @click="handleClick">
    <slot>{{ labelText }}</slot>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const classes = computed(() => [
  'action-btn',
  props.variant ? `action-btn--${props.variant}` : null,
  props.loading ? 'is-loading' : null
].filter(Boolean).join(' '))

const handleClick = (event) => {
  if (props.disabled || props.loading) return
  emit('click', event)
}

const labelText = computed(() => {
  if (props.loading) return props.label || 'Working…'
  return props.label
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
