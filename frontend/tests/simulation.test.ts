import { afterEach, describe, expect, it, vi } from 'vitest'
import { setCsrfToken } from '../src/api/http'
import { checkInputs, listAssets, saveSnapshot } from '../src/features/simulation/api'
import { parseCropFile, readInputFile, weatherHeader } from '../src/features/simulation/files'

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken('')
})

describe('input data boundary', () => {
  it('reads actual UTF-8 text, including Chinese content', async () => {
    const file = new File(['{"variety_name":"测试品种"}'], 'input.json')
    expect(await readInputFile(file)).toBe('{"variety_name":"测试品种"}')
    const csv = '\uFEFF' + weatherHeader + '\r\n2026-03-02,20,30,10,15,2,1.5\r\n'
    expect(await readInputFile(new File([csv], 'weather.csv'))).toBe(csv)
    expect(weatherHeader).toContain('vapor_kpa')
  })
  it('rejects oversized or invalid UTF-8 before sending data', async () => {
    await expect(readInputFile(new File(['a'.repeat(262145)], 'large.csv'))).rejects.toThrow(
      '256 KiB',
    )
    await expect(readInputFile(new File([new Uint8Array([255, 254])], 'bad.csv'))).rejects.toThrow(
      'UTF-8',
    )
  })
  it('accepts data objects and never evaluates scripts or arrays', () => {
    expect(parseCropFile('{"parameters":{"TSUM1":800}}')).toEqual({ parameters: { TSUM1: 800 } })
    expect(parseCropFile('\uFEFF{"parameters":{"TSUM1":800}}')).toEqual({
      parameters: { TSUM1: 800 },
    })
    expect(() => parseCropFile('alert("execute")')).toThrow('格式不正确')
    expect(() => parseCropFile('[]')).toThrow('品种')
    expect(() => parseCropFile('null')).toThrow('品种')
  })
  it('uses plot scope for weather and only team scope for crop parameters', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => Response.json({ items: [], total: 0, limit: 20, offset: 0 }))
    vi.stubGlobal('fetch', fetchMock)
    await listAssets('crop', 'a-plot')
    await listAssets('weather', 'a-plot', 20)
    expect(fetchMock.mock.calls[0]![0]).not.toContain('plot_id')
    expect(fetchMock.mock.calls[1]![0]).toContain('plot_id=a-plot')
    expect(fetchMock.mock.calls[1]![0]).toContain('offset=20')
  })
  it('sends explicit dates and exact versions with session-bound CSRF', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => Response.json({ input_ready: false }))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('test-csrf')
    const selection = {
      season_id: 'season',
      crop_asset_id: 'crop',
      soil_asset_id: 'soil',
      weather_asset_id: 'weather',
      emergence_date: '2026-03-02',
      cutoff_date: '2026-03-03',
    }
    await checkInputs(selection)
    await saveSnapshot(selection)
    expect(fetchMock.mock.calls[0]![1].headers.get('X-CSRF-Token')).toBe('test-csrf')
    expect(JSON.parse(fetchMock.mock.calls[1]![1].body)).toEqual(selection)
  })
})
