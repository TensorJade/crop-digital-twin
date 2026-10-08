/** Queue/poll requests reuse the authenticated HTTP boundary. */
import { jsonPost, requestJson } from '../../api/http'
import type { Page } from '../../api/types'
import type { RunDetail, RunSummary } from './runTypes'

export function listRuns(seasonId: string, offset = 0) {
  return requestJson<Page<RunSummary>>(
    '/api/v1/simulation-runs?' +
      new URLSearchParams({
        season_id: seasonId,
        limit: '20',
        offset: String(offset),
      }),
  )
}
export function getRun(id: string) {
  return requestJson<RunDetail>('/api/v1/simulation-runs/' + encodeURIComponent(id))
}
export function createRun(inputId: string, requestKey: string) {
  return requestJson<RunSummary>(
    '/api/v1/simulation-runs',
    jsonPost({
      input_id: inputId,
      request_key: requestKey,
      acknowledge_potential_only: true,
    }),
  )
}
