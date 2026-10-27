import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // The vendor file (React + Recharts) is ~190 kB gzipped, normal for a charting app.
    chunkSizeWarningLimit: 700,
    rolldownOptions: {
      output: {
        // Libraries change rarely: keep them in their own file so browsers can cache it
        // across app updates.
        codeSplitting: { groups: [{ name: 'vendor', test: /node_modules/ }] },
      },
    },
  },
  server: {
    // Same /api paths as on Vercel, so the frontend code needs no environment-specific URLs.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
