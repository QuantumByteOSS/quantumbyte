import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

// Pure-logic unit tests (no DOM, no DB). The @/ alias mirrors tsconfig paths.
export default defineConfig({
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
