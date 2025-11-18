<template>
  <nav class="task-bar">
    <RouterLink
      to="/"
      class="nav-btn"
      :class="{ active: currentRoute === 'search' }"
      title="Search for audiobooks"
    >
      🔍 Search
    </RouterLink>

    <RouterLink
      to="/history"
      class="nav-btn"
      :class="{ active: currentRoute === 'history' }"
      title="View download history and imports"
    >
      📋 History
    </RouterLink>

    <RouterLink
      to="/showcase"
      class="nav-btn"
      :class="{ active: currentRoute === 'showcase' }"
      title="Browse audiobooks in grid view"
    >
      🎭 Showcase
    </RouterLink>

    <RouterLink
      to="/logs"
      class="nav-btn"
      :class="{ active: currentRoute === 'logs' }"
      title="View application logs"
    >
      📄 Logs
    </RouterLink>

    <div class="task-bar-spacer"></div>

    <HealthIndicator :health="health" />
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import HealthIndicator from './HealthIndicator.vue'

defineProps({
  health: {
    type: Object,
    required: true,
    validator: (value) => {
      return typeof value.ok === 'boolean' && typeof value.checking === 'boolean'
    }
  }
})

const route = useRoute()
const currentRoute = computed(() => route.name)
</script>

<style scoped>
/* Component-specific styles if needed, otherwise uses main.css */
</style>
