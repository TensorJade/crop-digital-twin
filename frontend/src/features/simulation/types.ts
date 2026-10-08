/** Explicit input versions and preflight reports, separate from future simulation results. */
export type AssetKind = 'soil' | 'crop' | 'weather'
export interface InputAsset {
  id: string
  organization_id: string
  plot_id: string | null
  kind: AssetKind
  name: string
  source: string
  source_license: string
  content_hash: string
  created_at: string
}
export interface AssetDetail extends InputAsset {
  payload: Record<string, unknown>
}
export interface InputIssue {
  code: string
  message: string
}
export interface InputReport {
  input_ready: boolean
  simulation_available: boolean
  blocking_issues: InputIssue[]
  warnings: InputIssue[]
  missing_weather_days: number
  missing_parameters: string[]
}
export interface SnapshotSelection {
  season_id: string
  soil_asset_id: string
  crop_asset_id: string
  weather_asset_id: string
  emergence_date: string
  cutoff_date: string
}
export interface InputSnapshot {
  id: string
  season_id: string
  version: number
  content_hash: string
  created_at: string
  report: InputReport
}
export interface SnapshotDetail extends InputSnapshot {
  payload: Record<string, unknown>
}
export const assetLabels: Record<AssetKind, string> = {
  soil: '土壤资料',
  crop: '品种参数',
  weather: '天气资料',
}
export const selectionLabels: Record<AssetKind, string> = {
  soil: '本田土壤资料',
  crop: '本季品种参数',
  weather: '本田天气资料',
}
