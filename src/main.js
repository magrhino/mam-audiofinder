/**
 * Vue 3 Application Entry Point
 * Main initialization for MAM Audiobook Finder
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)

app.mount('#app')
