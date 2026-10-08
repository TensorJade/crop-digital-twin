import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestJson, setCsrfToken, setUnauthorizedHandler } from '../src/api/http'
import { createUser, login, logout } from '../src/features/identity/api'

afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken('')
  setUnauthorizedHandler(undefined)
})

describe('identity HTTP boundary', () => {
  it('uses same-origin cookies and sends session-bound CSRF on writes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ id: 'member' }))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('memory-only-csrf')
    await createUser({
      username: 'reader',
      display_name: '成员',
      password: 'long-test-passphrase',
      role: 'viewer',
    })
    const options = fetchMock.mock.calls[0]![1]
    expect(options.credentials).toBe('same-origin')
    expect(options.headers.get('X-CSRF-Token')).toBe('memory-only-csrf')
    expect(JSON.parse(options.body)).not.toHaveProperty('organization_id')
  })
  it('does not clear the current session for incorrect login credentials', async () => {
    const expired = vi.fn()
    setUnauthorizedHandler(expired)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ detail: { message: '账号或密码错误' } }, { status: 401 }),
        ),
    )
    await expect(login('reader', 'wrong-password')).rejects.toMatchObject({ status: 401 })
    expect(expired).not.toHaveBeenCalled()
  })
  it('lets the app clear stale account data when an authenticated route rejects the session', async () => {
    const expired = vi.fn()
    setUnauthorizedHandler(expired)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(Response.json({ detail: { message: '请重新登录' } }, { status: 401 })),
    )
    await expect(requestJson('/api/v1/plots')).rejects.toMatchObject({ status: 401 })
    expect(expired).toHaveBeenCalledOnce()
  })
  it('cleared CSRF is not reused by a subsequent logout request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ message: '已退出登录' }))
    vi.stubGlobal('fetch', fetchMock)
    setCsrfToken('previous-session')
    setCsrfToken('')
    await logout()
    expect(fetchMock.mock.calls[0]![1].headers.has('X-CSRF-Token')).toBe(false)
  })
  it('a delayed previous-session rejection does not clear a newly accepted identity', async () => {
    const expired = vi.fn()
    setUnauthorizedHandler(expired)
    let finishRequest!: (response: Response) => void
    const response = new Promise<Response>((resolve) => {
      finishRequest = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(response))
    setCsrfToken('previous-session')
    const assertion = expect(requestJson('/api/v1/plots')).rejects.toMatchObject({ status: 401 })
    setCsrfToken('new-session')
    finishRequest(Response.json({ detail: { message: '请重新登录' } }, { status: 401 }))
    await assertion
    expect(expired).not.toHaveBeenCalled()
  })
  it('presents an actionable network error without echoing the request credentials', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('transport failure')))
    await expect(login('reader', 'private-test-password')).rejects.toMatchObject({
      message: '无法连接服务，请检查网络后重试',
      status: 0,
    })
  })
})
