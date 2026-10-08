import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { request as httpRequest } from 'node:http'
import { apiLogin, authorizedPost, browserLogin, testPassword } from './helpers'

const pageErrors = new WeakMap<Page, string[]>()
test.beforeEach(({ page }) => {
  const messages: string[] = []
  pageErrors.set(page, messages)
  page.on('pageerror', (error) => messages.push(error.message))
})
test.afterEach(({ page }) => expect(pageErrors.get(page)).toEqual([]))

test('administrator creates a reader, sees audit history, and reader has no write controls', async ({
  page,
  request,
}) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '登录我的农田', exact: true })).toBeVisible()
  await expect(page.locator('.plot-choice')).toHaveCount(0)
  mkdirSync('../runtime', { recursive: true })
  await page.screenshot({ path: '../runtime/login-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/login-mobile.png', fullPage: true })
  await page.setViewportSize({ width: 1280, height: 720 })
  await apiLogin(request)
  const name = `权限验收田-${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/plots', {
        name,
        area_mu: '15',
        latitude: 23.1,
        longitude: 113.2,
      })
    ).status(),
  ).toBe(201)
  await browserLogin(page)
  await page.getByRole('button', { name: '成员与操作记录', exact: true }).click()
  await page.getByRole('button', { name: '建立成员账号', exact: true }).click()
  const username = `reader_${Date.now()}`
  await page.getByLabel('成员账号', { exact: true }).fill(username)
  await page.getByLabel('成员称呼', { exact: true }).fill('只读验收成员')
  await page.getByRole('combobox', { name: '成员权限', exact: true }).selectOption('viewer')
  await page.getByLabel('初始密码', { exact: true }).fill(testPassword)
  await page.getByRole('button', { name: '保存成员', exact: true }).click()
  await expect(page.locator('.member-entry').filter({ hasText: username })).toContainText('仅查看')
  await expect(
    page.locator('.audit-entry').filter({ hasText: '建立成员账号' }).first(),
  ).toBeVisible()
  mkdirSync('../runtime', { recursive: true })
  await page.screenshot({ path: '../runtime/members-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.screenshot({ path: '../runtime/members-mobile.png', fullPage: true })
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await browserLogin(page, username)
  await expect(page.locator('.plot-choice').filter({ hasText: name })).toBeVisible()
  await expect(page.getByRole('button', { name: '登记地块', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '建立种植季', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '成员与操作记录', exact: true })).toHaveCount(0)
})

test('password change clears the workspace and requires the new password after reload', async ({
  page,
  request,
}) => {
  await apiLogin(request)
  const username = `operator_${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/users', {
        username,
        display_name: '密码验收成员',
        password: testPassword,
        role: 'operator',
      })
    ).status(),
  ).toBe(201)
  await browserLogin(page, username)
  await page.reload()
  await expect(page.getByRole('heading', { name: '我的农田', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '修改密码', exact: true }).click()
  await page.getByLabel('当前密码', { exact: true }).fill(testPassword)
  await page.getByLabel('新密码', { exact: true }).fill('changed-e2e-test-passphrase')
  await page.getByLabel('再次填写新密码', { exact: true }).fill('changed-e2e-test-passphrase')
  await page.getByRole('button', { name: '保存新密码', exact: true }).click()
  await expect(page.getByRole('heading', { name: '登录我的农田', exact: true })).toBeVisible()
  await expect(page.locator('.plot-choice')).toHaveCount(0)
  await page.getByLabel('账号', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(testPassword)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('账号或密码错误')
  await page.getByLabel('密码', { exact: true }).fill('changed-e2e-test-passphrase')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('heading', { name: '我的农田', exact: true })).toBeVisible()
})

test('different organizations never display each others plots', async ({ page, request }) => {
  await apiLogin(request)
  const firstName = `本组织田-${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/plots', {
        name: firstName,
        area_mu: '15',
        latitude: 23.1,
        longitude: 113.2,
      })
    ).status(),
  ).toBe(201)
  await apiLogin(request, 'e2e_other')
  const secondName = `另一组织田-${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/plots', {
        name: secondName,
        area_mu: '15',
        latitude: 23.1,
        longitude: 113.2,
      })
    ).status(),
  ).toBe(201)
  await browserLogin(page)
  await expect(page.locator('.plot-choice').filter({ hasText: firstName })).toBeVisible()
  await expect(page.locator('.plot-choice').filter({ hasText: secondName })).toHaveCount(0)
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await browserLogin(page, 'e2e_other')
  await expect(page.locator('.plot-choice').filter({ hasText: secondName })).toBeVisible()
  await expect(page.locator('.plot-choice').filter({ hasText: firstName })).toHaveCount(0)
})

test('administrator deactivation ends a members current session and reactivation permits a new login', async ({
  page,
  request,
  browser,
}) => {
  await apiLogin(request)
  const username = `active_${Date.now()}`
  expect(
    (
      await authorizedPost(request, '/api/v1/users', {
        username,
        display_name: '停用验收成员',
        password: testPassword,
        role: 'operator',
      })
    ).status(),
  ).toBe(201)
  await browserLogin(page)
  const memberContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5179' })
  try {
    const memberPage = await memberContext.newPage()
    await browserLogin(memberPage, username)
    await page.getByRole('button', { name: '成员与操作记录', exact: true }).click()
    const row = page.locator('.member-entry').filter({ hasText: username })
    await row.getByRole('button', { name: '停用 停用验收成员', exact: true }).click()
    await row.getByRole('button', { name: '确认停用', exact: true }).click()
    await expect(row).toContainText('已停用')
    await memberPage.reload()
    await expect(
      memberPage.getByRole('heading', { name: '登录我的农田', exact: true }),
    ).toBeVisible()
    await expect(memberPage.locator('.plot-choice')).toHaveCount(0)
    await row.getByRole('button', { name: '启用 停用验收成员', exact: true }).click()
    await expect(row).toContainText('已启用')
    await browserLogin(memberPage, username)
  } finally {
    await memberContext.close()
  }
})

async function isolatedSourceLogin(password: string, forwarded: string) {
  // A real second loopback source isolates this failure window from every other test.
  return new Promise<{ status: number; retryAfter: string | undefined }>((resolve, reject) => {
    const body = JSON.stringify({ username: 'e2e_owner', password })
    const request = httpRequest(
      'http://127.0.0.1:8019/api/v1/auth/login',
      {
        localAddress: '127.0.0.2',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
          'X-Forwarded-For': forwarded,
        },
      },
      (response) => {
        response.resume()
        resolve({ status: response.statusCode || 0, retryAfter: response.headers['retry-after'] })
      },
    )
    request.on('error', reject)
    request.end(body)
  })
}

test('changing forwarded headers cannot bypass the direct connection login failure limit', async () => {
  for (let attempt = 0; attempt < 5; ++attempt) {
    const response = await isolatedSourceLogin('invalid-e2e-passphrase', `192.0.2.${attempt + 1}`)
    expect(response.status).toBe(401)
  }
  const response = await isolatedSourceLogin(testPassword, '192.0.2.200')
  expect(response.status).toBe(429)
  expect(response.retryAfter).toBe('900')
})
