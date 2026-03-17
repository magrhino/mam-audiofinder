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
  padding: 0.4rem 0.85rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--btn-secondary-border);
  background: var(--btn-secondary-bg);
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.action-btn:hover:not(:disabled) {
  background: var(--btn-secondary-hover);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.action-btn--primary {
  background: var(--btn-primary-bg);
  border-color: var(--btn-primary-border);
  box-shadow: var(--btn-primary-shadow);
}

.action-btn--primary:hover:not(:disabled) {
  background: var(--btn-primary-hover);
  border-color: rgba(220, 100, 100, 0.85);
  box-shadow: 0 6px 16px rgba(120, 30, 30, 0.5);
}

.action-btn--secondary {
  background: var(--btn-secondary-bg);
  border-color: var(--btn-secondary-border);
}

.action-btn--secondary:hover:not(:disabled) {
  background: var(--btn-secondary-hover);
  border-color: rgba(255, 255, 255, 0.3);
}

.action-btn--danger {
  background: var(--btn-error-bg);
  border-color: var(--btn-error-border);
  box-shadow: var(--btn-error-shadow);
}

.action-btn--danger:hover:not(:disabled) {
  background: rgba(190, 70, 70, 0.95);
  border-color: rgba(240, 100, 100, 0.85);
  box-shadow: 0 6px 14px rgba(170, 55, 55, 0.4);
}

.action-btn--success {
  background: var(--btn-success-bg);
  border-color: var(--btn-success-border);
  box-shadow: var(--btn-success-shadow);
}

.action-btn--success:hover:not(:disabled) {
  background: rgba(55, 140, 75, 0.95);
  border-color: rgba(100, 200, 120, 0.85);
  box-shadow: 0 6px 14px rgba(45, 120, 65, 0.4);
}

.action-btn--info {
  background: var(--btn-info-bg);
  border-color: var(--btn-info-border);
}

.action-btn--info:hover:not(:disabled) {
  background: rgba(90, 120, 180, 0.95);
  border-color: rgba(140, 180, 240, 0.85);
}

.action-btn--warning {
  background: var(--btn-warning-bg);
  border-color: var(--btn-warning-border);
}

.action-btn--warning:hover:not(:disabled) {
  background: rgba(200, 140, 60, 0.95);
  border-color: rgba(240, 180, 100, 0.85);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.action-btn.is-loading {
  opacity: 0.8;
  cursor: wait;
}

/* Focus ring for accessibility */
.action-btn:focus-visible {
  outline: 2px solid rgba(200, 80, 80, 0.8);
  outline-offset: 2px;
}
</style>
