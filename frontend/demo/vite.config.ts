import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  build: { assetsInlineLimit: 0, license: { fileName: 'THIRD_PARTY_LICENSES.md' } },
});
