import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: { browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL },
});
