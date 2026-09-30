import { devtools } from '@tanstack/devtools-vite';
import { tanstackStart } from '@tanstack/react-start/plugin/vite';
import viteReact from '@vitejs/plugin-react';

import { nitro } from 'nitro/vite';

import { defineConfig } from 'vite';

const config = defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [devtools(), tanstackStart(), nitro({ preset: 'node-server' }), viteReact()],
  server:  {
    proxy: {
      '/api':   'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
});

export default config;
