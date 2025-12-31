<template>
  <n-button-group class="view-toggle">
    <n-tooltip trigger="hover" placement="bottom">
      <template #trigger>
        <n-button
          :type="modelValue === 'table' ? 'primary' : 'default'"
          :class="{ 'active': modelValue === 'table' }"
          class="toggle-btn"
          @click="setMode('table')"
        >
          <template #icon>
            <span class="toggle-icon">≡</span>
          </template>
        </n-button>
      </template>
      Table View
    </n-tooltip>

    <n-tooltip trigger="hover" placement="bottom">
      <template #trigger>
        <n-button
          :type="modelValue === 'cards' ? 'primary' : 'default'"
          :class="{ 'active': modelValue === 'cards' }"
          class="toggle-btn"
          @click="setMode('cards')"
        >
          <template #icon>
            <span class="toggle-icon">⊞</span>
          </template>
        </n-button>
      </template>
      Cards View
    </n-tooltip>
  </n-button-group>
</template>

<script setup>
import { NButtonGroup, NButton, NTooltip } from 'naive-ui'

defineProps({
  modelValue: {
    type: String,
    required: true,
    validator: (value) => ['cards', 'table'].includes(value)
  }
})

const emit = defineEmits(['update:modelValue'])

const setMode = (mode) => {
  emit('update:modelValue', mode)
}
</script>

<style scoped>
.view-toggle {
  display: flex;
}

.toggle-btn {
  min-width: 40px;
  height: 34px;
  background: rgba(42, 42, 42, 0.5) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  transition: all 0.3s ease;
}

.toggle-btn:first-child {
  border-radius: 8px 0 0 8px !important;
}

.toggle-btn:last-child {
  border-radius: 0 8px 8px 0 !important;
}

.toggle-btn:hover:not(.active) {
  background: rgba(42, 42, 42, 0.7) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
}

.toggle-btn.active {
  background: rgba(80, 0, 0, 0.6) !important;
  border-color: rgba(106, 0, 0, 0.7) !important;
  color: white !important;
  box-shadow:
    0 4px 12px rgba(80, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.toggle-icon {
  font-size: 16px;
  line-height: 1;
}

/* Override Naive UI button group borders */
:deep(.n-button-group .n-button:not(:first-child):not(:last-child)) {
  border-radius: 0 !important;
}

:deep(.n-button-group .n-button + .n-button) {
  margin-left: -1px;
}
</style>
