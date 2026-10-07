import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  define: {
    // Version des builds de release (tag sans « v ») : l'app Android la compare
    // à la dernière release GitHub pour proposer la mise à jour.
    __APP_VERSION__: JSON.stringify(process.env.APP_VERSION ?? ''),
  },
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8001',
      '/media': 'http://localhost:8001',
    },
  },
  test: {
    setupFiles: ['./src/test-setup.ts'],
    // Les tests Playwright (e2e/) ont leur propre runner — vitest les ignore.
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
  },
})
