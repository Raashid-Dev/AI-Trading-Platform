import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // base is '/AI-Trading-Platform/' on GitHub Pages, '/' everywhere else
  base: process.env.VITE_BASE_URL || '/',
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 800,
  },
  server: {
    port: 3000,
    // Dev proxy — mirrors production: all /state /ws etc. go to local backend
    proxy: {
      '/ws':      { target: 'ws://localhost:8000',   ws: true,        changeOrigin: true },
      '/state':   { target: 'http://localhost:8000', changeOrigin: true },
      '/signals': { target: 'http://localhost:8000', changeOrigin: true },
      '/trades':  { target: 'http://localhost:8000', changeOrigin: true },
      '/summary': { target: 'http://localhost:8000', changeOrigin: true },
      '/capital': { target: 'http://localhost:8000', changeOrigin: true },
      '/health':  { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
