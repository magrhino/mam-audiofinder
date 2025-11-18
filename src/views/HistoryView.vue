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
import HistoryRow from '@components/HistoryRow.vue'
import { useHistoryLiveUpdates } from '@composables/useHistoryLiveUpdates'

// Use the live updates composable for auto-refresh and event handling
// - Auto-refreshes every 5 seconds to show live torrent status
// - Listens to 'torrentAdded' events for immediate updates
// - Automatically cleans up interval and listeners on unmount
// - Exposes start/stop methods for future router integration (pause on navigation)
const { history, loadHistory } = useHistoryLiveUpdates({ interval: 5000 })
</script>

<style scoped>
/* Uses main.css styles */
</style>
