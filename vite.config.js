import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/components', import.meta.url)),
      '@views': fileURLToPath(new URL('./src/views', import.meta.url)),
      '@core': fileURLToPath(new URL('./app/static/js/core', import.meta.url)),
      '@services': fileURLToPath(new URL('./app/static/js/services', import.meta.url)),
      '@composables': fileURLToPath(new URL('./src/composables', import.meta.url))
    }
  },
  build: {
    outDir: 'app/static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      }
    },
    // Generate manifest for asset URLs
    manifest: true
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/search': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/add': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/import': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/qb': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/covers': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/config': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
