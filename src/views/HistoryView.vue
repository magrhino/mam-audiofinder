<template>
  <div class="history-view card">
    <h3>Download History & Imports</h3>
    <table>
      <thead>
        <tr>
          <th style="width: 80px">Cover</th>
          <th>Title</th>
          <th>Author</th>
          <th>Narrator</th>
          <th class="center">Link</th>
          <th>When</th>
          <th>Status</th>
          <th>Import</th>
          <th>Verify</th>
          <th>Remove</th>
        </tr>
      </thead>
      <tbody>
        <HistoryRow v-for="entry in history" :key="entry.id" :item="entry" :column-count="10" @updated="loadHistory" />
        <tr v-if="!history.length">
          <td colspan="10" class="center muted">No items in history yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import HistoryRow from '@components/HistoryRow.vue'
import { useApi } from '@composables/useApi'

const api = useApi()
const history = ref([])

const loadHistory = async () => {
  try {
    const data = await api.getHistory()
    history.value = data.items || []
  } catch (err) {
    console.error('Failed to load history', err)
  }
}

onMounted(() => {
  loadHistory()
  // Reload history when torrents are added
  window.addEventListener('torrentAdded', loadHistory)
})
</script>

<style scoped>
/* Uses main.css styles */
</style>
