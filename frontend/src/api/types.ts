/** Public API process liveness response; not database or model readiness. */
export interface HealthResponse {
  status: 'ok'
  service: 'crop-twin-api'
  version: string
  scope: 'process'
}
