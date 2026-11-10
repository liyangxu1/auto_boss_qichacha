import { defineConfig } from 'vite';

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  server: { proxy: { '/api': 'http://127.0.0.1:8765' } },
  build: { outDir: '../autoboss/web/static', emptyOutDir: true },
});
