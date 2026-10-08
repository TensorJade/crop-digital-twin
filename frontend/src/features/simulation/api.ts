/** Input requests reuse the common session/CSRF boundary; sources are never fetched by URL. */
import { jsonPost, requestJson } from '../../api/http'
import type { Page } from '../../api/types'
import type {
  AssetDetail,
  AssetKind,
  InputAsset,
  InputReport,
  InputSnapshot,
  SnapshotDetail,
  SnapshotSelection,
} from './types'

export function listAssets(kind: AssetKind, plotId: string, offset = 0) {
  const query = new URLSearchParams({ kind, limit: '20', offset: String(offset) })
  if (kind !== 'crop') query.set('plot_id', plotId)
  return requestJson<Page<InputAsset>>(`/api/v1/input-assets?${query}`)
}
export function createAsset(data: Record<string, unknown>) {
  return requestJson<AssetDetail>('/api/v1/input-assets', jsonPost(data))
}
export function checkInputs(data: SnapshotSelection) {
  return requestJson<InputReport>('/api/v1/simulation-inputs/check', jsonPost(data))
}
export function saveSnapshot(data: SnapshotSelection) {
  return requestJson<SnapshotDetail>('/api/v1/simulation-inputs', jsonPost(data))
}
export function listSnapshots(seasonId: string, offset = 0) {
  return requestJson<Page<InputSnapshot>>(
    `/api/v1/simulation-inputs?${new URLSearchParams({ season_id: seasonId, limit: '20', offset: String(offset) })}`,
  )
}
export function getSnapshot(id: string) {
  return requestJson<SnapshotDetail>(`/api/v1/simulation-inputs/${encodeURIComponent(id)}`)
}
