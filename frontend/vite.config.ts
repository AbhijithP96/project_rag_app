import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks:   undefined,
        entryFileNames: 'assets/ask-docs-widget.js',
        chunkFileNames: 'assets/ask-docs-widget-[hash].js',
        assetFileNames: 'assets/ask-docs-widget[extname]',
      },
    },
    assetsInlineLimit: 102400,
    sourcemap:         false,
    target:            'es2020',
  },
  server: {
    port: 5173,
  },
})