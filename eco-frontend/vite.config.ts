
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  // Keep the F1 admin API proxy
  server: {
    proxy: {
      '/admin/benchmark/': 'http://127.0.0.1:8000'
    }
  },

  // Vitest: exclude Playwright E2E tests
  test: {
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**'
    ]
  }
})
