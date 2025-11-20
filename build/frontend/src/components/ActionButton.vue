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
.action-btn {
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  color: var(--text-primary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.action-btn--primary {
  background: var(--btn-primary-bg);
  border-color: transparent;
}

.action-btn--secondary {
  background: rgba(255, 255, 255, 0.05);
}

.action-btn--danger {
  background: rgba(168, 50, 50, 0.2);
  border-color: #a83232;
}

.action-btn--success {
  background: rgba(45, 122, 62, 0.2);
  border-color: var(--success);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
