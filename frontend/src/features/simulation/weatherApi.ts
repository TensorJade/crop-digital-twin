/** Fixed server-side sources, with plot scope; clients cannot submit remote URLs. */
import { requestJson } from '../../api/http'

export interface WeatherDay {
  date: string
  tmin_c: number
  tmax_c: number
  rain_mm: number
  radiation_mj_m2: number
  wind_m_s: number
  vapor_kpa: number
}
export interface WeatherPreview {
  asset: {
    kind: 'weather'
    plot_id: string
    name: string
    source: string
    source_license: string
    data: Record<string, unknown>
  }
  day_count: number
  sample_days: WeatherDay[]
  warnings: string[]
}
export interface StationCandidate {
  station_id: string
  name: string
  distance_km: number
  coverage_start: string
  coverage_end: string
  observations_connected: false
}
export interface StationList {
  source: string
  source_url: string
  catalog_hash: string
  retrieved_at: string
  radius_km: number
  stations: StationCandidate[]
  notice: string
}
export function previewWeather(plotId: string, start: string, end: string) {
  return requestJson<WeatherPreview>(
    '/api/v1/weather/preview?' +
      new URLSearchParams({ plot_id: plotId, start_date: start, end_date: end }),
  )
}
export function nearbyStations(plotId: string) {
  return requestJson<StationList>(
    '/api/v1/weather/stations?' + new URLSearchParams({ plot_id: plotId }),
  )
}
