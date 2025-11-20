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
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge--success {
  background: rgba(45, 122, 62, 0.2);
  color: var(--success);
}

.status-badge--warning {
  background: rgba(184, 115, 51, 0.2);
  color: var(--warning);
}

.status-badge--danger {
  background: rgba(168, 50, 50, 0.2);
  color: var(--error);
}

.status-badge--info {
  background: rgba(79, 138, 255, 0.2);
  color: #9faed6;
}

.status-badge--muted {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}
</style>
