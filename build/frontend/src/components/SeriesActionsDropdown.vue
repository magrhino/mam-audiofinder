<script setup>
import { h } from 'vue'
import { NDropdown, NButton } from 'naive-ui'
import { useRouter } from 'vue-router'

const props = defineProps({
  series: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['viewBooks', 'findMissing', 'editLink', 'refresh'])
const router = useRouter()

const options = [
  {
    label: 'View Books',
    key: 'view',
    icon: () => h('span', { style: 'margin-right: 8px' }, '📚'),
  },
  {
    label: 'Find Missing',
    key: 'missing',
    icon: () => h('span', { style: 'margin-right: 8px' }, '🔍'),
  },
  {
    type: 'divider',
    key: 'd1',
  },
  {
    label: 'Change Hardcover Link',
    key: 'link',
    icon: () => h('span', { style: 'margin-right: 8px' }, '🔗'),
  },
  {
    label: 'Refresh Data',
    key: 'refresh',
    icon: () => h('span', { style: 'margin-right: 8px' }, '🔄'),
  },
]

function handleSelect(key) {
  switch (key) {
    case 'view':
      // Navigate to SeriesView with pre-populated search
      router.push({
        name: 'series',
        query: {
          title: props.series.name,
          limit: '20',
          ...(props.series.hardcover_series_id && {
            series_id: props.series.hardcover_series_id,
          }),
        },
      })
      break
    case 'missing':
      emit('findMissing', props.series.name, props.series.hardcover_series_id)
      break
    case 'link':
      emit('editLink', props.series)
      break
    case 'refresh':
      emit('refresh', props.series)
      break
  }
}
</script>

<template>
  <NDropdown
    trigger="click"
    :options="options"
    placement="bottom-end"
    @select="handleSelect"
  >
    <NButton size="small" quaternary class="actions-btn">
      <span class="btn-icon">⚙️</span>
      <span class="btn-caret">▾</span>
    </NButton>
  </NDropdown>
</template>

<style scoped>
.actions-btn {
  padding: 4px 8px;
  min-width: auto;
}

.btn-icon {
  font-size: 14px;
}

.btn-caret {
  font-size: 10px;
  margin-left: 4px;
  opacity: 0.7;
}
</style>
