import { defineConfig } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

const temporaryDirectory = mkdtempSync(path.join(tmpdir(), 'crop-twin-e2e-'))
const pythonExecutable =
  process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  outputDir: '../test-results',
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5179',
    browserName: 'chromium',
    channel: process.env.CROP_TWIN_TEST_BROWSER || undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: `"${pythonExecutable}" ../scripts/e2e_api.py`,
      cwd: '.',
      url: 'http://127.0.0.1:8019/api/v1/health',
      reuseExistingServer: false,
      env: {
        CROP_TWIN_ENVIRONMENT: 'test',
        CROP_TWIN_DATABASE_URL: `sqlite:///${path.join(temporaryDirectory, 'farm.db').replaceAll('\\', '/')}`,
      },
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5179 --strictPort',
      url: 'http://127.0.0.1:5179',
      reuseExistingServer: false,
      env: { CROP_TWIN_DEV_API_URL: 'http://127.0.0.1:8019' },
    },
  ],
})
