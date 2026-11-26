import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  publicDir: false,
  build: {
    outDir: fileURLToPath(new URL('../nexa_scriptguard/gui_assets/modern', import.meta.url)),
    emptyOutDir: true,
    assetsInlineLimit: 0,
    modulePreload: false,
    cssCodeSplit: false,
    license: { fileName: 'THIRD_PARTY_LICENSES.md' },
    rolldownOptions: {
      output: {
        entryFileNames: 'phase4.js',
        assetFileNames: ({ names }) => names.some(name => name.endsWith('.css'))
          ? 'phase4.css' : 'phase4-[name][extname]',
      },
    },
  },
});
