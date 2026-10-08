import type { HealthResponse } from './types'

/** Check process liveness and reject transport failures or incompatible responses. */
export async function getApiHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health')
  if (!response.ok) {
    throw new Error(`后端请求失败（HTTP ${response.status}）`)
  }
  const payload: unknown = await response.json()
  if (
    typeof payload !== 'object' ||
    payload === null ||
    !('status' in payload) ||
    payload.status !== 'ok' ||
    !('service' in payload) ||
    payload.service !== 'crop-twin-api' ||
    !('version' in payload) ||
    typeof payload.version !== 'string' ||
    !('scope' in payload) ||
    payload.scope !== 'process'
  ) {
    throw new Error('后端响应与接口契约不一致')
  }
  return payload as HealthResponse
}
