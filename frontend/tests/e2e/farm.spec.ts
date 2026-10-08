import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const errors = new WeakMap<Page, string[]>()
test.beforeEach(async ({ page }) => {
  const messages: string[] = []
  errors.set(page, messages)
  page.on('pageerror', (error) => messages.push(error.message))
})
test.afterEach(async ({ page }) => {
  expect(errors.get(page)).toEqual([])
})

async function registerPlot(page: Page, plotName: string) {
  const openForm = page.getByRole('button', { name: '登记地块', exact: true })
  if (await openForm.isVisible()) await openForm.click()
  await page.getByLabel('地块名称', { exact: true }).fill(plotName)
  await page.getByLabel('面积（亩）', { exact: true }).fill('15')
  await page.getByLabel('纬度', { exact: true }).fill('23.1')
  await page.getByLabel('经度', { exact: true }).fill('113.2')
  await page.getByRole('button', { name: '保存地块', exact: true }).click()
  await expect(page.locator('.plot-choice').filter({ hasText: plotName })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByRole('heading', { name: '选择种植季', exact: true })).toBeVisible()
}

async function establishSeason(page: Page, date: string, variety: string) {
  const openForm = page.getByRole('button', { name: '建立种植季', exact: true })
  if (await openForm.isVisible()) await openForm.click()
  await page.getByRole('combobox', { name: '种植方式', exact: true }).selectOption('transplanting')
  await page.getByLabel('播种 / 移栽日期', { exact: true }).fill(date)
  await page.getByLabel('水稻品种（选填）', { exact: true }).fill(variety)
  await page.getByRole('button', { name: '保存种植季', exact: true }).click()
  await expect(page.locator('.season-choice').filter({ hasText: variety })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByRole('heading', { name: '农事记录', exact: true })).toBeVisible()
}

test('register, record, correct, retain history, reload, close and start the next rice season', async ({
  page,
}) => {
  const plotName = `验收田-${Date.now()}`
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '我的农田', exact: true })).toBeVisible()
  await registerPlot(page, plotName)
  await establishSeason(page, '2026-03-01', '验收品种一')
  await page.getByRole('button', { name: '登记农事', exact: true }).click()
  await page.getByRole('combobox', { name: '农事类型', exact: true }).selectOption('irrigation')
  await page.getByLabel('农事日期', { exact: true }).fill('2026-03-10')
  await page.getByLabel('数量', { exact: true }).fill('100')
  await page.getByRole('combobox', { name: '单位', exact: true }).selectOption('m3')
  await page.getByLabel('备注（选填）', { exact: true }).fill('验收灌溉记录')
  await page.getByRole('button', { name: '保存农事', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: '农事已保存' })).toBeVisible()
  await expect(page.locator('.record-quantity')).toContainText('100 立方米')
  await expect(page.locator('.record-quantity')).toContainText('10 毫米')

  await page.getByRole('button', { name: '修正 2026-03-10 灌溉', exact: true }).click()
  await page.getByLabel('数量', { exact: true }).fill('150')
  await page.getByLabel('修正原因', { exact: true }).fill('验收数量修正')
  await page.getByRole('button', { name: '保存修正', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: '原始记录已保留' })).toBeVisible()
  await expect(page.locator('.ledger-entry')).toHaveCount(1)
  await expect(page.locator('.record-quantity')).toContainText('150 立方米')
  await page.getByLabel('查看修订历史', { exact: true }).check()
  await expect(page.locator('.ledger-entry')).toHaveCount(2)
  await expect(page.getByText('旧记录', { exact: true })).toBeVisible()

  await page.reload()
  await expect(page.locator('.ledger-entry')).toHaveCount(1)
  await expect(page.locator('.record-quantity')).toContainText('150 立方米')
  mkdirSync(path.resolve('../runtime'), { recursive: true })
  await page.screenshot({ path: '../runtime/farm-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/farm-mobile.png', fullPage: true })

  await page.getByRole('button', { name: '结束当前种植季', exact: true }).click()
  await page.getByLabel('实际结束日期', { exact: true }).fill('2026-06-30')
  await page.getByRole('button', { name: '确认结束该季', exact: true }).click()
  await expect(page.locator('.season-choice').filter({ hasText: '验收品种一' })).toContainText(
    '已结束',
  )
  await establishSeason(page, '2026-07-01', '验收品种二')
  await expect(page.locator('.ledger-entry')).toHaveCount(0)
})

test('failed initial load is actionable and retry restores the real plot list', async ({
  page,
  request,
}) => {
  const name = `重试田-${Date.now()}`
  const seed = await request.post('/api/v1/plots', {
    data: { name, area_mu: '15', latitude: 23.1, longitude: 113.2 },
  })
  expect(seed.status()).toBe(201)
  await page.route('**/api/v1/plots?*', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: {
          code: 'STORAGE_UNAVAILABLE',
          message: '数据存储暂不可用，请检查数据库初始化或连接',
        },
      }),
    }),
  )
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('数据存储暂不可用')
  await page.unroute('**/api/v1/plots?*')
  await page.getByRole('button', { name: '重新读取', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.plot-choice').filter({ hasText: name })).toBeVisible()
})

test('a delayed response from the previous plot cannot replace the newly selected season', async ({
  page,
  request,
}) => {
  const timestamp = Date.now()
  const makePlot = async (name: string) => {
    const result = await request.post('/api/v1/plots', {
      data: { name, area_mu: '15', latitude: 23.1, longitude: 113.2 },
    })
    expect(result.status()).toBe(201)
    const plot = await result.json()
    const season = await request.post('/api/v1/seasons', {
      data: {
        plot_id: plot.id,
        start_date: '2026-03-01',
        establishment_method: 'transplanting',
        variety_name: name,
      },
    })
    expect(season.status()).toBe(201)
    return plot.id as string
  }
  const firstName = `慢响应田-${timestamp}`
  const secondName = `新选择田-${timestamp}`
  const firstId = await makePlot(firstName)
  await makePlot(secondName)
  await page.goto('/')
  await expect(page.locator('.season-choice')).toContainText(secondName)
  let releaseDelay = () => {}
  const delay = new Promise<void>((resolve) => {
    releaseDelay = resolve
  })
  let signalStarted = () => {}
  const started = new Promise<void>((resolve) => {
    signalStarted = resolve
  })
  await page.route('**/api/v1/seasons?*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('plot_id') === firstId) {
      signalStarted()
      await delay
      await route.continue()
    } else await route.continue()
  })
  await page.locator('.plot-choice').filter({ hasText: firstName }).click()
  await started
  await page.locator('.plot-choice').filter({ hasText: secondName }).click()
  await expect(page.locator('.season-choice')).toContainText(secondName)
  const previousResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/seasons?') &&
      new URL(response.url()).searchParams.get('plot_id') === firstId,
  )
  releaseDelay()
  await (await previousResponse).finished()
  await expect(page.locator('.season-choice')).toContainText(secondName)
  await expect(page.locator('.season-choice').filter({ hasText: firstName })).toHaveCount(0)
})

test('retry also reloads a failed season request when the plot selection is unchanged', async ({
  page,
  request,
}) => {
  const name = `种植季重试田-${Date.now()}`
  const result = await request.post('/api/v1/plots', {
    data: { name, area_mu: '15', latitude: 23.1, longitude: 113.2 },
  })
  expect(result.status()).toBe(201)
  const plot = await result.json()
  const season = await request.post('/api/v1/seasons', {
    data: {
      plot_id: plot.id,
      start_date: '2026-03-01',
      establishment_method: 'transplanting',
      variety_name: name,
    },
  })
  expect(season.status()).toBe(201)
  await page.route('**/api/v1/seasons?*', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: { code: 'STORAGE_UNAVAILABLE', message: '种植季暂不可用' } }),
    }),
  )
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('种植季暂不可用')
  await page.unroute('**/api/v1/seasons?*')
  await page.getByRole('button', { name: '重新读取', exact: true }).click()
  await expect(page.locator('.season-choice')).toContainText(name)
  await expect(page.getByRole('alert')).toHaveCount(0)
})
