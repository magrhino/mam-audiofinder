<script setup>
import { h } from 'vue'
import { useRouter } from 'vue-router'
import { NDataTable, NButton, NTag, NSpace } from 'naive-ui'

const props = defineProps({
  series: { type: Array, required: true },
})

const emit = defineEmits(['diff'])
const router = useRouter()

function viewSeries(seriesName, hardcoverSeriesId) {
  // Navigate to SeriesView with pre-populated search
  router.push({
    name: 'series',
    query: {
      title: seriesName,
      limit: '20',
      ...(hardcoverSeriesId && { series_id: hardcoverSeriesId }),
    },
  })
}

const columns = [
  {
    title: 'Series',
    key: 'name',
    sorter: 'default',
  },
  {
    title: 'Author',
    key: 'author',
    width: 200,
  },
  {
    title: 'Books',
    key: 'book_count',
    width: 120,
    align: 'center',
    render: (row) => {
      const absCount = row.abs_book_count ?? row.book_count
      const seriesCount = row.series_book_count ?? row.book_count
      return `${absCount ?? 0} / ${seriesCount ?? 0}`
    },
  },
  {
    title: 'Source',
    key: 'source',
    width: 100,
    render: (row) => h(NTag, { size: 'small', type: row.source === 'abs' ? 'success' : 'info' }, () => row.source.toUpperCase()),
  },
  {
    title: 'Actions',
    key: 'actions',
    width: 200,
    render: (row) => h(
      NSpace,
      { size: 'small' },
      () => [
        h(
          NButton,
          {
            size: 'small',
            onClick: () => viewSeries(row.name, row.hardcover_series_id),
          },
          () => 'View Series'
        ),
        h(
          NButton,
          {
            size: 'small',
            onClick: () => emit('diff', row.name, row.hardcover_series_id),
          },
          () => 'Find Missing'
        ),
      ]
    ),
  },
]
</script>

<template>
  <NDataTable
    :columns="columns"
    :data="series"
    :row-key="row => row.id"
    :single-line="false"
    striped
  />
</template>
