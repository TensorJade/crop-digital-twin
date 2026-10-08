import { afterEach, describe, expect, it, vi } from 'vitest'
import { createEvent, correctEvent, listEvents } from '../src/features/farm/api'
import { ApiError, requestJson } from '../src/api/http'
import { localDate } from '../src/features/farm/types'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('farm API boundary', () => {
  it('keeps original quantities and units in POST data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ id: 'event' }))
    vi.stubGlobal('fetch', fetchMock)
    await createEvent('season', {
      event_type: 'irrigation',
      occurred_on: '2026-03-10',
      quantity: 100,
      unit: 'm3',
      material_name: null,
      notes: '',
    })
    const [url, options] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/v1/management-events')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toMatchObject({
      season_id: 'season',
      quantity: 100,
      unit: 'm3',
    })
  })

  it('sends corrections to a new revision endpoint with a reason', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ id: 'revision' }))
    vi.stubGlobal('fetch', fetchMock)
    await correctEvent(
      'previous',
      {
        event_type: 'inspection',
        occurred_on: '2026-03-10',
        quantity: null,
        unit: null,
        material_name: null,
        notes: '巡田',
      },
      '修正类型',
    )
    expect(fetchMock.mock.calls[0]![0]).toBe('/api/v1/management-events/previous/corrections')
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body).correction_reason).toBe('修正类型')
  })

  it('retains pagination and explicit history selection', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json({ items: [], total: 0, limit: 20, offset: 20 }))
    vi.stubGlobal('fetch', fetchMock)
    await listEvents('season', 20, true)
    expect(fetchMock.mock.calls[0]![0]).toContain('offset=20&include_history=true')
  })

  it('exposes safe business errors and status for conflict handling', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          Response.json(
            { detail: { code: 'STALE_REVISION', message: '请刷新后选择最新记录' } },
            { status: 409 },
          ),
        ),
    )
    await expect(requestJson('/api/v1/plots')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: '请刷新后选择最新记录',
    })
  })

  it('rejects a success response that has no JSON body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not json')))
    await expect(requestJson('/api/v1/plots')).rejects.toBeInstanceOf(ApiError)
  })

  it('uses local year/month/day for the form default', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 9, 8, 0, 5))
    expect(localDate()).toBe('2026-10-08')
  })
})
