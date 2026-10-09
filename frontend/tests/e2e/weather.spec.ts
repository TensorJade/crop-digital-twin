import { expect, test } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { apiLogin, authorizedPost, browserLogin } from './helpers'

const source = JSON.parse(readFileSync('../tests/fixtures/potential-input.json', 'utf8'))

test('preview grid weather, inspect station catalogue, export and seal source then run real PCSE', async ({
  page,
  request,
}, testInfo) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await apiLogin(request)
  const name = '天气链路验收田-' + Date.now()
  const plot = await (
    await authorizedPost(request, '/api/v1/plots', {
      name,
      area_mu: '10',
      latitude: 23.1,
      longitude: 113.2,
    })
  ).json()
  await authorizedPost(request, '/api/v1/seasons', {
    plot_id: plot.id,
    start_date: '2024-03-01',
    establishment_method: 'direct_sowing',
    variety_name: source.season.variety_name,
  })
  for (const [kind, data] of [
    ['soil', { wilting_point: 0.1, field_capacity: 0.3, saturation: 0.5, depth_cm: 100 }],
    ['crop', source.assets.crop.payload],
  ]) {
    await authorizedPost(request, '/api/v1/input-assets', {
      kind,
      data,
      plot_id: kind === 'crop' ? null : plot.id,
      name: '天气链路合成资料',
      source: '自有软件验收资料',
      source_license: '仅软件测试',
    })
  }
  await browserLogin(page)
  await page.locator('.plot-choice').filter({ hasText: name }).click()
  await page.getByRole('button', { name: '模拟资料', exact: true }).click()
  await page.getByRole('button', { name: '按农田位置获取天气', exact: true }).click()
  await page.getByLabel('天气起始日期').fill('2024-03-02')
  await page.getByLabel('天气结束日期').fill('2024-03-03')
  let failOnce = true
  await page.route('**/api/v1/weather/preview?**', async (route) => {
    if (failOnce) {
      failOnce = false
      await route.fulfill({
        status: 503,
        json: { detail: { message: '天气源暂不可用，请稍后重试' } },
      })
    } else await route.continue()
  })
  await page.getByRole('button', { name: '获取并预览天气', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('天气源暂不可用')
  await page.getByRole('button', { name: '获取并预览天气', exact: true }).click()
  await expect(page.getByRole('region', { name: '网格天气预览' })).toContainText('2天资料已获取')
  await expect(page.getByRole('region', { name: '网格天气预览' })).toContainText('软件验收合成响应')
  await page.getByRole('button', { name: '查找附近气象站', exact: true }).click()
  await expect(page.locator('.weather-stations')).toContainText('SOFTWARE TEST STATION A')
  await expect(page.locator('.weather-stations')).toContainText('观测尚未接入')
  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载逐日CSV', exact: true }).click()
  const exported = testInfo.outputPath('grid-weather.csv')
  await (await downloadEvent).saveAs(exported)
  const csv = readFileSync(exported, 'utf8')
  expect(csv.trim().split('\n')).toHaveLength(3)
  const firstDay = csv.trim().split('\n')[1]!.split(',')
  expect(firstDay[0]).toBe('2024-03-02')
  expect(firstDay.slice(1, 6).map(Number)).toEqual([20, 22.3, 2.4, 12, 2])
  mkdirSync('../runtime', { recursive: true })
  await page.screenshot({ path: '../runtime/weather-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/weather-mobile.png', fullPage: true })
  await page.getByText('模型计算资料（可稍后补齐）', { exact: true }).click()
  await page.getByLabel('Angstrom A', { exact: true }).fill('0.29')
  await page.getByLabel('Angstrom B', { exact: true }).fill('0.49')
  await page.getByRole('button', { name: '保存为本地天气资料', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('资料已保存')
  const saved = await (
    await request.get(
      '/api/v1/input-assets?' + new URLSearchParams({ kind: 'weather', plot_id: plot.id }),
    )
  ).json()
  const detail = await (await request.get('/api/v1/input-assets/' + saved.items[0].id)).json()
  expect(detail.payload.source_kind).toBe('gridded')
  expect(detail.payload.station_id).toBeNull()
  expect(detail.payload.provider.raw_response.header.sources).toContain('crop_twin_test')
  await page.getByLabel('实际出苗日期').fill('2024-03-02')
  await page.getByLabel('资料截止日期').fill('2024-03-03')
  await page.getByRole('button', { name: '保存输入快照', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('输入快照第')
  await page.getByRole('button', { name: '生长计算', exact: true }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '开始潜在生长计算', exact: true }).click()
  await expect(page.getByRole('region', { name: '当前计算任务' })).toContainText('计算完成', {
    timeout: 20000,
  })
  await expect(page.locator('.growth-result')).toContainText('2024-03-03')
  const season = await (await request.get('/api/v1/seasons?plot_id=' + plot.id)).json()
  const runs = await (
    await request.get('/api/v1/simulation-runs?season_id=' + season.items[0].id)
  ).json()
  const completed = await (await request.get('/api/v1/simulation-runs/' + runs.items[0].id)).json()
  expect(completed.result.daily).toHaveLength(2)
  expect(completed.result.weather_method.source_kind).toBe('gridded')
  expect(completed.result.weather_method.raw_hash).toBe(detail.payload.provider.raw_hash)
  expect(pageErrors).toEqual([])
})
