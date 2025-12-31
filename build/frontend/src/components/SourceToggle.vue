<script setup>
import { computed } from 'vue'
import { NButtonGroup, NButton, NTooltip } from 'naive-ui'

const props = defineProps({
  modelValue: { type: String, default: 'abs' },
  absConfigured: Boolean,
  hardcoverConfigured: Boolean,
})

const emit = defineEmits(['update:modelValue'])

const options = computed(() => [
  { value: 'abs', label: 'ABS', disabled: !props.absConfigured, tip: 'AudioBookShelf library' },
  { value: 'hardcover', label: 'Hardcover', disabled: !props.hardcoverConfigured, tip: 'Hardcover catalog' },
  { value: 'both', label: 'Both', disabled: !props.absConfigured || !props.hardcoverConfigured, tip: 'Cross-reference' },
])

function select(val) {
  const opt = options.value.find(o => o.value === val)
  if (opt && !opt.disabled) {
    emit('update:modelValue', val)
  }
}
</script>

<template>
  <NButtonGroup size="small">
    <NTooltip v-for="opt in options" :key="opt.value" trigger="hover">
      <template #trigger>
        <NButton
          :type="modelValue === opt.value ? 'primary' : 'default'"
          :disabled="opt.disabled"
          @click="select(opt.value)"
        >
          {{ opt.label }}
        </NButton>
      </template>
      {{ opt.tip }}
    </NTooltip>
  </NButtonGroup>
</template>
