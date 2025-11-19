/**
 * Vue 3 Application Entry Point
 * Main initialization for MAM Audiobook Finder
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Naive UI uses CSS-in-JS, no need to import styles separately

const app = createApp(App)

app.use(router)

app.mount('#app')
