<script setup>
import { computed } from 'vue'
import { NSelect } from 'naive-ui'

const props = defineProps({
  modelValue: {
    type: String,
    default: null
  },
  libraries: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const options = computed(() => {
  const opts = [
    { label: 'All Libraries', value: null }
  ]

  for (const lib of props.libraries) {
    if (lib.enabled) {
      opts.push({
        label: lib.name,
        value: lib.id
      })
    }
  }

  return opts
})

function handleChange(value) {
  emit('update:modelValue', value)
}
</script>

<template>
  <NSelect
    :value="modelValue"
    :options="options"
    :loading="loading"
    size="small"
    style="width: 180px"
    placeholder="Select library"
    @update:value="handleChange"
  />
</template>
