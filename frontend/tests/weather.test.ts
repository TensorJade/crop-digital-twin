import { afterEach, expect, it, vi } from 'vitest'
import { nearbyStations, previewWeather } from '../src/features/simulation/weatherApi'

afterEach(() => vi.unstubAllGlobals())

it('requests weather by scoped plot and explicit dates without a source URL', async () => {
  const fetch = vi.fn().mockImplementation(async () => Response.json({ day_count: 2 }))
  vi.stubGlobal('fetch', fetch)
  await previewWeather('plot/one', '2024-03-02', '2024-03-03')
  const url = new URL(fetch.mock.calls[0]![0], 'http://localhost')
  expect(url.pathname).toBe('/api/v1/weather/preview')
  expect(url.searchParams.get('plot_id')).toBe('plot/one')
  expect(url.searchParams.get('start_date')).toBe('2024-03-02')
  expect(url.searchParams.get('end_date')).toBe('2024-03-03')
  expect(url.searchParams.has('url')).toBe(false)
})

it('shows a safe upstream error and keeps station lookup independent', async () => {
  const fetch = vi
    .fn()
    .mockImplementationOnce(async () =>
      Response.json({ detail: { message: '天气源暂不可用' } }, { status: 503 }),
    )
    .mockImplementationOnce(async () => Response.json({ stations: [] }))
  vi.stubGlobal('fetch', fetch)
  await expect(previewWeather('plot', '2024-03-02', '2024-03-03')).rejects.toThrow('天气源暂不可用')
  await nearbyStations('plot')
  expect(fetch.mock.calls[1]![0]).toContain('/api/v1/weather/stations?plot_id=plot')
})
