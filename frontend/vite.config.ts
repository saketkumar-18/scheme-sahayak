import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev proxy: same-origin /api calls hit the local backend
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
