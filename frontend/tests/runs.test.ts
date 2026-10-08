import { afterEach, expect, it, vi } from 'vitest'
import { setCsrfToken } from '../src/api/http'
import { createRun, getRun, listRuns } from '../src/features/simulation/runApi'

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken('')
})
it('submits a stable request key and explicit potential acknowledgement with CSRF', async () => {
  const fetch = vi.fn().mockImplementation(async () => Response.json({ status: 'queued' }))
  vi.stubGlobal('fetch', fetch)
  setCsrfToken('test-csrf')
  await createRun('input-version', 'same-request')
  expect(JSON.parse(fetch.mock.calls[0]![1].body)).toEqual({
    input_id: 'input-version',
    request_key: 'same-request',
    acknowledge_potential_only: true,
  })
  expect(fetch.mock.calls[0]![1].headers.get('X-CSRF-Token')).toBe('test-csrf')
})
it('queries one season and encodes result IDs', async () => {
  const fetch = vi.fn().mockImplementation(async () => Response.json({ items: [] }))
  vi.stubGlobal('fetch', fetch)
  await listRuns('season', 20)
  await getRun('id/other')
  expect(fetch.mock.calls[0]![0]).toContain('season_id=season')
  expect(fetch.mock.calls[0]![0]).toContain('offset=20')
  expect(fetch.mock.calls[1]![0]).toContain('id%2Fother')
})
