import { expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'

/** Only scripts/e2e_api.py's guarded, temporary test database has these accounts. */
export const testPassword = 'e2e-only-test-passphrase'
const csrfByRequest = new WeakMap<APIRequestContext, string>()

export async function apiLogin(
  request: APIRequestContext,
  username = 'e2e_owner',
  password = testPassword,
) {
  const response = await request.post('/api/v1/auth/login', { data: { username, password } })
  expect(response.status()).toBe(200)
  const identity = await response.json()
  csrfByRequest.set(request, identity.csrf_token)
  return identity
}

export async function authorizedPost(request: APIRequestContext, url: string, data: unknown) {
  return request.post(url, { data, headers: { 'X-CSRF-Token': csrfByRequest.get(request) || '' } })
}

export async function browserLogin(page: Page, username = 'e2e_owner', password = testPassword) {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '登录我的农田', exact: true })).toBeVisible()
  await page.getByLabel('账号', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('heading', { name: '我的农田', exact: true })).toBeVisible()
}
