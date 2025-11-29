import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  server: {
    proxy: {
      '/predict': 'http://localhost:5000',
      '/store_scan': 'http://localhost:5000',
      '/update_grain_category': 'http://localhost:5000',
      '/categories': 'http://localhost:5000',
      '/summary_statistics': 'http://localhost:5000',
      '/grain_distribution': 'http://localhost:5000',
      '/scan_history': 'http://localhost:5000',
      '/activate': 'http://localhost:5000',
      '/varieties': 'http://localhost:5000',
      '/api': {
        target: 'https://staging.agreap.com',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '/admin/web/v3'),
      },
      '/admin/web/v3': {
        target: 'https://staging.agreap.com',
        changeOrigin: true,
        secure: false,
      },
      '/agsure/backend': {
        target: 'https://staging.agreap.com',
        changeOrigin: true,
        secure: false,
      }
    },
  },
})