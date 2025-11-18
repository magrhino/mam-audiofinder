<template>
  <n-config-provider :theme="darkTheme" :theme-overrides="customTheme">
    <n-global-style />
    <div id="app">
      <NavBar :health="healthStatus" />

      <header>
        <h1>📚 Audiobook Finder</h1>
        <span class="muted">Download Audiobooks and Import to Audiobookshelf</span>
      </header>

      <RouterView />
    </div>
  </n-config-provider>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { darkTheme, NConfigProvider, NGlobalStyle } from 'naive-ui'
import { customTheme } from './theme/naive'
import NavBar from '@components/NavBar.vue'
import { useApi } from '@composables/useApi'

const healthStatus = ref({ ok: false, checking: true })
const api = useApi()

const checkHealth = async () => {
  try {
    const health = await api.health()
    healthStatus.value = { ok: health.ok, checking: false }
  } catch (error) {
    console.error('Health check failed:', error)
    healthStatus.value = { ok: false, checking: false }
  }
}

onMounted(() => {
  checkHealth()
  // Check health every 30 seconds
  setInterval(checkHealth, 30000)
})
</script>

<style>
/* Global app styles are loaded from /static/css/main.css */
</style>
