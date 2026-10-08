/** Transport types mirror the versioned OpenAPI, including decimal strings. */
export type { Page } from '../../api/types'

export interface Plot {
  id: string
  organization_id: string
  name: string
  area_mu: string
  area_ha: string
  latitude: number
  longitude: number
  created_at: string
}

export interface PlotInput {
  name: string
  area_mu: number
  latitude: number
  longitude: number
}

export type EstablishmentMethod = 'direct_sowing' | 'transplanting'
export interface Season {
  id: string
  plot_id: string
  crop_code: 'rice'
  start_date: string
  end_date: string | null
  establishment_method: EstablishmentMethod
  variety_name: string | null
  created_at: string
}

export interface SeasonInput {
  plot_id: string
  start_date: string
  establishment_method: EstablishmentMethod
  variety_name: string | null
  end_date?: string | null
}

export type EventType =
  'sowing' | 'transplanting' | 'irrigation' | 'fertilization' | 'inspection' | 'harvest'
export type InputUnit = 'mm' | 'm3' | 'kg/mu' | 'kg/ha'
export interface EventInput {
  event_type: EventType
  occurred_on: string
  quantity: number | null
  unit: InputUnit | null
  material_name: string | null
  notes: string
}

export interface ManagementEvent {
  id: string
  season_id: string
  event_type: EventType
  occurred_on: string
  quantity: string | null
  unit: InputUnit | null
  normalized_quantity: string | null
  normalized_unit: 'mm' | 'kg/ha' | null
  material_name: string | null
  notes: string
  created_at: string
  revision: number
  replaces_event_id: string | null
  correction_reason: string | null
  is_current: boolean
}

export const eventLabels: Record<EventType, string> = {
  sowing: '播种',
  transplanting: '移栽',
  irrigation: '灌溉',
  fertilization: '施肥',
  inspection: '巡田',
  harvest: '收获',
}
export const unitLabels: Record<InputUnit, string> = {
  mm: '毫米',
  m3: '立方米',
  'kg/mu': '千克/亩',
  'kg/ha': '千克/公顷',
}

/** Use the farmer's local calendar day rather than truncating a UTC timestamp. */
export function localDate(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

/** Format an exact transport decimal for a compact, readable field label. */
export function displayQuantity(value: string | number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 6 }).format(Number(value))
}
