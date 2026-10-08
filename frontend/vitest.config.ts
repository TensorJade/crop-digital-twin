import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfiguration from './vite.config.ts'

export default mergeConfig(
  viteConfiguration,
  defineConfig({
    test: { include: ['tests/**/*.test.ts'] },
  }),
)
