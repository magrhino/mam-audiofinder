<template>
  <table>
    <thead>
      <tr>
        <th>Series</th>
        <th>Author</th>
        <th class="center">Books</th>
        <th class="center">Readers</th>
        <th class="center">Action</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in items" :key="item.series_id">
        <td>{{ item.series_name }}</td>
        <td>{{ item.author_name }}</td>
        <td class="center">{{ item.book_count }}</td>
        <td class="center">{{ item.readers_count?.toLocaleString?.() || item.readers_count }}</td>
        <td class="center">
          <ActionButton label="View" variant="primary" @click="handleClick(item)" />
        </td>
      </tr>
      <tr v-if="!items.length">
        <td colspan="5" class="center muted">No series yet.</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
import ActionButton from './ActionButton.vue'

defineProps({
  items: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select'])

const handleClick = (item) => emit('select', item)
</script>

<style scoped>
/* Uses main.css styles */
</style>
