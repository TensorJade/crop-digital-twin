/** Public API process liveness response; not database or model readiness. */
export interface HealthResponse {
  status: 'ok'
  service: 'crop-twin-api'
  version: string
  scope: 'process'
}

/** Shared pagination transport without coupling identity and farm modules. */
export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
