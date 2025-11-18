import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/frontend/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: [
        'app/static/js/**/*.js'
      ],
      exclude: [
        '**/*.test.js',
        '**/*.spec.js',
        '**/tests/**'
      ]
    },
    alias: {
      '@': fileURLToPath(new URL('./app/static/js', import.meta.url)),
      '@core': fileURLToPath(new URL('./app/static/js/core', import.meta.url)),
      '@services': fileURLToPath(new URL('./app/static/js/services', import.meta.url)),
      '@components': fileURLToPath(new URL('./app/static/js/components', import.meta.url)),
      '@views': fileURLToPath(new URL('./app/static/js/views', import.meta.url))
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./app/static/js', import.meta.url)),
      '@core': fileURLToPath(new URL('./app/static/js/core', import.meta.url)),
      '@services': fileURLToPath(new URL('./app/static/js/services', import.meta.url)),
      '@components': fileURLToPath(new URL('./app/static/js/components', import.meta.url)),
      '@views': fileURLToPath(new URL('./app/static/js/views', import.meta.url))
    }
  }
});
