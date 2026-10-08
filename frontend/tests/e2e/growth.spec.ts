import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { apiLogin, authorizedPost, browserLogin, testPassword } from './helpers'
import type { APIRequestContext, Page } from '@playwright/test'

const source = JSON.parse(readFileSync('../tests/fixtures/potential-input.json', 'utf8'))
const pageErrors = new WeakMap<Page, string[]>()
test.beforeEach(({ page }) => {
  const errors: string[] = []
  pageErrors.set(page, errors)
  page.on('pageerror', (error) => errors.push(error.message))
})
test.afterEach(({ page }) => expect(pageErrors.get(page)).toEqual([]))

async function prepare(request: APIRequestContext) {
  await apiLogin(request)
  const name = '模型接口验收田-' + Date.now()
  const plot = await (
    await authorizedPost(request, '/api/v1/plots', {
      name,
      area_mu: '15',
      latitude: 23.1,
      longitude: 113.2,
    })
  ).json()
  const season = await (
    await authorizedPost(request, '/api/v1/seasons', {
      plot_id: plot.id,
      start_date: '2026-03-01',
      establishment_method: 'direct_sowing',
      variety_name: source.season.variety_name,
    })
  ).json()
  const weather = { ...source.assets.weather.payload }
  const columns = [
    'date',
    'tmin_c',
    'tmax_c',
    'rain_mm',
    'radiation_mj_m2',
    'wind_m_s',
    'vapor_kpa',
  ]
  weather.csv_text =
    columns.join(',') +
    '\n' +
    weather.days
      .map((day: Record<string, string | number>) => columns.map((key) => day[key]).join(','))
      .join('\n')
  delete weather.days
  const selection: Record<string, string> = { season_id: season.id, ...source.period }
  for (const [kind, data] of [
    ['soil', { wilting_point: 0.1, field_capacity: 0.3, saturation: 0.5, depth_cm: 100 }],
    ['crop', source.assets.crop.payload],
    ['weather', weather],
  ]) {
    const asset = await (
      await authorizedPost(request, '/api/v1/input-assets', {
        kind,
        name: '测试专用资料',
        plot_id: kind === 'crop' ? null : plot.id,
        source: '自有合成资料，仅验证软件',
        source_license: '测试专用，非真实农田数据',
        data,
      })
    ).json()
    selection[kind + '_asset_id'] = asset.id
  }
  const snapshot = await (
    await authorizedPost(request, '/api/v1/simulation-inputs', selection)
  ).json()
  return { name, season, snapshot }
}

test('queue real PCSE, watch daily results, inspect curve and verify exported calculation', async ({
  page,
  request,
}, testInfo) => {
  const farm = await prepare(request)
  await browserLogin(page)
  await page.locator('.plot-choice').filter({ hasText: farm.name }).click()
  await page.getByRole('button', { name: '生长计算', exact: true }).click()
  await expect(page.getByRole('button', { name: '开始潜在生长计算', exact: true })).toBeDisabled()
  await expect(page.getByLabel('用于计算的输入快照')).toContainText('可计算潜在生长')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: '开始潜在生长计算', exact: true }).click()
  await expect(page.getByRole('region', { name: '当前计算任务' })).toContainText('计算完成', {
    timeout: 20000,
  })
  await expect(page.getByRole('region', { name: '逐日潜在生长结果' })).toContainText('2026-03-16')
  const slider = page.getByRole('slider', { name: '查看日期' })
  await slider.fill('0')
  await expect(page.getByRole('heading', { name: '潜在生长 · 2026-03-02' })).toBeVisible()
  await expect(page.locator('.growth-values')).toContainText('0.22')
  await slider.fill('14')
  await page.getByLabel('曲线指标').selectOption('above_ground_kg_ha')
  await expect(page.getByRole('img', { name: '地上部干物质（kg/公顷）逐日曲线' })).toBeVisible()
  mkdirSync('../runtime', { recursive: true })
  await page.screenshot({ path: '../runtime/growth-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/growth-mobile.png', fullPage: true })
  const event = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载计算结果', exact: true }).click()
  const exported = testInfo.outputPath('growth-result.json')
  await (await event).saveAs(exported)
  const document = JSON.parse(readFileSync(exported, 'utf8'))
  expect(document.payload.simulation_executed).toBe(true)
  expect(document.payload.agronomically_validated).toBe(false)
  expect(document.payload.daily).toHaveLength(15)
  const python = path.resolve(
    process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python',
  )
  expect(
    execFileSync(python, ['scripts/verify_input.py', exported], {
      cwd: path.resolve('..'),
      encoding: 'utf8',
    }),
  ).toContain('PASS')
  await page.reload()
  await page.getByRole('button', { name: '生长计算', exact: true }).click()
  await expect(page.locator('.growth-result')).toContainText('2026-03-16')
})

test('a reader can inspect a completed calculation and download it, with no queue control', async ({
  page,
  request,
}) => {
  const farm = await prepare(request)
  const queued = await (
    await authorizedPost(request, '/api/v1/simulation-runs', {
      input_id: farm.snapshot.id,
      request_key: crypto.randomUUID(),
      acknowledge_potential_only: true,
    })
  ).json()
  await expect
    .poll(
      async () => (await (await request.get('/api/v1/simulation-runs/' + queued.id)).json()).status,
      { timeout: 20000 },
    )
    .toBe('succeeded')
  const username = 'growth_reader_' + Date.now()
  await authorizedPost(request, '/api/v1/users', {
    username,
    display_name: '模型验收只读',
    password: testPassword,
    role: 'viewer',
  })
  await browserLogin(page, username)
  await page.locator('.plot-choice').filter({ hasText: farm.name }).click()
  await page.getByRole('button', { name: '生长计算', exact: true }).click()
  await expect(page.locator('.growth-result')).toContainText('2026-03-16')
  await expect(page.getByRole('button', { name: '开始潜在生长计算', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '下载计算结果', exact: true })).toBeVisible()
})
