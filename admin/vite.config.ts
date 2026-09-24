import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The app reads ../targets.yml for brand tiers, so the dev server may serve the repo root.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, fs: { allow: ['..'] } },
})
