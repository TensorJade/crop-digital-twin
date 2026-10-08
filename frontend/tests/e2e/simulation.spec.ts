import { expect, test } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import { mkdirSync, readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { apiLogin, authorizedPost, browserLogin, testPassword } from './helpers'

const cropData = {
  crop_code: 'rice',
  model_code: 'WOFOST72',
  variety_name: '输入浏览器验收品种',
  applicable_region: '软件验收合成数据',
  parameters: { TSUM1: 800 },
}
const csv =
  'date,tmin_c,tmax_c,rain_mm,radiation_mj_m2,wind_m_s,vapor_kpa\n2026-03-02,20,30,10,15,2,1.5'
const errors = new WeakMap<Page, string[]>()
test.beforeEach(({ page }) => {
  const messages: string[] = []
  errors.set(page, messages)
  page.on('pageerror', (error) => messages.push(error.message))
})
test.afterEach(({ page }) => expect(errors.get(page)).toEqual([]))

async function createTestFarm(request: APIRequestContext) {
  await apiLogin(request)
  const name = `输入验收田-${Date.now()}`
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
      variety_name: cropData.variety_name,
    })
  ).json()
  return { plot, season, name }
}

async function sourceFields(page: Page, name: string) {
  await page.getByLabel('资料名称', { exact: true }).fill(name)
  await page.getByLabel('资料来源', { exact: true }).fill('浏览器验收合成资料')
  await page.getByLabel('使用许可说明', { exact: true }).fill('测试专用，非生产数据')
}

test('import soil crop and weather, check gaps, freeze and verify a browser-exported snapshot', async ({
  page,
  request,
}, testInfo) => {
  const farm = await createTestFarm(request)
  await browserLogin(page)
  await page.locator('.plot-choice').filter({ hasText: farm.name }).click()
  await page.getByRole('button', { name: '模拟资料', exact: true }).click()
  await expect(page.getByRole('heading', { name: '模拟输入资料', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '登记土壤', exact: true }).click()
  await sourceFields(page, '软件验收土壤')
  await page.getByLabel('萎蔫点（体积比）', { exact: true }).fill('0.1')
  await page.getByLabel('田间持水量（体积比）', { exact: true }).fill('0.3')
  await page.getByLabel('饱和含水量（体积比）', { exact: true }).fill('0.5')
  await page.getByLabel('土层深度（cm）', { exact: true }).fill('100')
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('combobox', { name: '本田土壤资料', exact: true })).toContainText(
    '软件验收土壤',
  )
  await page.getByRole('button', { name: '导入品种', exact: true }).click()
  await sourceFields(page, '软件验收参数')
  await page.getByLabel('品种参数文件（JSON）', { exact: true }).setInputFiles({
    name: 'test-rice.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(cropData)),
  })
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('combobox', { name: '本季品种参数', exact: true })).toContainText(
    '软件验收参数',
  )
  await page.getByRole('button', { name: '导入天气', exact: true }).click()
  await sourceFields(page, '软件验收天气')
  await page.getByLabel('逐日天气文件（CSV）', { exact: true }).setInputFiles({
    name: 'bad.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csv + '\n2026-03-02,20,30,10,15,2,1.5'),
  })
  await page.getByLabel('气象站编号', { exact: true }).fill('TEST-ONLY')
  await page.getByLabel('天气来源纬度', { exact: true }).fill('23.1')
  await page.getByLabel('天气来源经度', { exact: true }).fill('113.2')
  await page.getByLabel('天气来源海拔（m）', { exact: true }).fill('10')
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('日期重复')
  await page
    .getByLabel('逐日天气文件（CSV）', { exact: true })
    .setInputFiles({ name: 'test-weather.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
  await page.getByRole('button', { name: '保存资料', exact: true }).click()
  await expect(page.getByRole('combobox', { name: '本田天气资料', exact: true })).toContainText(
    '软件验收天气',
  )
  await page.getByLabel('实际出苗日期', { exact: true }).fill('2026-03-02')
  await page.getByLabel('资料截止日期', { exact: true }).fill('2026-03-03')
  await page.getByRole('button', { name: '检查输入资料', exact: true }).click()
  await expect(page.locator('.input-report')).toContainText('缺少 1 天天气')
  await page.getByRole('button', { name: '保存输入快照', exact: true }).click()
  await expect(page.locator('.input-snapshot-row').first()).toContainText('第 1 版')
  mkdirSync('../runtime', { recursive: true })
  await page.screenshot({ path: '../runtime/inputs-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/inputs-mobile.png', fullPage: true })
  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载第 1 版', exact: true }).click()
  const download = await downloadEvent
  const destination = testInfo.outputPath('exported-input.json')
  await download.saveAs(destination)
  const exported = JSON.parse(readFileSync(destination, 'utf8'))
  expect(exported.payload.simulation_executed).toBe(false)
  const python = path.resolve(
    process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python',
  )
  const output = execFileSync(python, ['scripts/verify_input.py', destination], {
    cwd: path.resolve('..'),
    encoding: 'utf8',
  })
  expect(output).toContain('PASS')
  await page.reload()
  await page.getByRole('button', { name: '模拟资料', exact: true }).click()
  await expect(page.locator('.input-snapshot-row').first()).toContainText('第 1 版')
})

test('a reader can download input history and cannot import or save versions', async ({
  page,
  request,
}) => {
  const { plot, season, name } = await createTestFarm(request)
  const selected: Record<string, string> = {
    season_id: season.id,
    emergence_date: '2026-03-02',
    cutoff_date: '2026-03-02',
  }
  const common = { source: '软件验收', source_license: '测试专用' }
  for (const [kind, data] of [
    ['soil', { wilting_point: 0.1, field_capacity: 0.3, saturation: 0.5, depth_cm: 100 }],
    ['crop', cropData],
    [
      'weather',
      {
        source_kind: 'station',
        station_id: 'TEST-ONLY',
        latitude: 23.1,
        longitude: 113.2,
        elevation_m: 10,
        time_basis: 'Asia/Shanghai',
        csv_text: csv,
      },
    ],
  ] as const) {
    const response = await authorizedPost(request, '/api/v1/input-assets', {
      ...common,
      kind,
      plot_id: kind === 'crop' ? null : plot.id,
      name: `只读验收${kind}`,
      data,
    })
    expect(response.status()).toBe(201)
    selected[`${kind}_asset_id`] = (await response.json()).id
  }
  expect((await authorizedPost(request, '/api/v1/simulation-inputs', selected)).status()).toBe(201)
  const username = `input_reader_${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/users', {
        username,
        display_name: '只读输入验收',
        password: testPassword,
        role: 'viewer',
      })
    ).status(),
  ).toBe(201)
  await browserLogin(page, username)
  await page.locator('.plot-choice').filter({ hasText: name }).click()
  await page.getByRole('button', { name: '模拟资料', exact: true }).click()
  await expect(page.locator('.input-snapshot-row')).toContainText('第 1 版')
  await expect(page.getByRole('button', { name: '保存输入快照', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '登记土壤', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '导入品种', exact: true })).toHaveCount(0)
  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载第 1 版', exact: true }).click()
  expect((await downloadEvent).suggestedFilename()).toContain('rice-input-v1')
})
