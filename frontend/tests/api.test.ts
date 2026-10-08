import { afterEach, describe, expect, it, vi } from 'vitest'
import { getApiHealth } from '../src/api/client'

afterEach(() => vi.unstubAllGlobals())

describe('API health client', () => {
  it('rejects HTTP failures instead of showing connected', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))
    await expect(getApiHealth()).rejects.toThrow('HTTP 503')
  })

  it('rejects an unrelated JSON response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ status: 'ok' })))
    await expect(getApiHealth()).rejects.toThrow('接口契约不一致')
  })

  it('accepts the process-liveness contract', async () => {
    const health = { status: 'ok', service: 'crop-twin-api', version: '0.1.0', scope: 'process' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(health)))
    await expect(getApiHealth()).resolves.toEqual(health)
  })
})
