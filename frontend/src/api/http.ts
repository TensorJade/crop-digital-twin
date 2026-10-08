/** Small shared HTTP boundary; no store, repository, or business rules in the browser. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

let csrfToken = ''
let unauthorizedHandler: (() => void) | undefined

/** Keep only the session-bound CSRF value in memory; the auth Cookie is HttpOnly. */
export function setCsrfToken(token: string) {
  csrfToken = token
}

/** The app owns session expiry UI; the HTTP boundary does not import the identity feature. */
export function setUnauthorizedHandler(handler: (() => void) | undefined) {
  unauthorizedHandler = handler
}

function errorMessage(payload: unknown, status: number): string {
  if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
    const detail = payload.detail
    if (typeof detail === 'string') return detail
    if (
      typeof detail === 'object' &&
      detail !== null &&
      'message' in detail &&
      typeof detail.message === 'string'
    ) {
      return detail.message
    }
    if (Array.isArray(detail)) return '请检查必填项、数值范围和日期格式'
  }
  return status === 503 ? '数据存储暂不可用，请检查服务后重试' : `保存或读取失败（HTTP ${status}）`
}

/** Request JSON and expose safe API errors; network errors remain errors to the caller. */
export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const requestCsrfToken = csrfToken
  const headers = new Headers(options.headers)
  if (options.method?.toUpperCase() === 'POST' && requestCsrfToken)
    headers.set('X-CSRF-Token', requestCsrfToken)
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' }).catch(
    () => {
      throw new ApiError('无法连接服务，请检查网络后重试', 0)
    },
  )
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    // A delayed response from the previous login must not clear the new identity.
    if (response.status === 401 && path !== '/api/v1/auth/login' && requestCsrfToken === csrfToken)
      unauthorizedHandler?.()
    throw new ApiError(errorMessage(payload, response.status), response.status)
  }
  if (payload === null) throw new ApiError('服务返回格式不正确，请稍后重试', response.status)
  return payload as T
}

/** Build an explicit JSON POST request without a mutable shared configuration object. */
export function jsonPost(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}
