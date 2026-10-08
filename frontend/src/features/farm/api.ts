import { jsonPost, requestJson } from '../../api/http'
import type {
  EventInput,
  ManagementEvent,
  Page,
  Plot,
  PlotInput,
  Season,
  SeasonInput,
} from './types'

const BASE = '/api/v1'

/** Retrieve one bounded plot page. */
export function listPlots(offset = 0): Promise<Page<Plot>> {
  return requestJson(`${BASE}/plots?limit=20&offset=${offset}`)
}
/** Save a reported plot. */
export function createPlot(input: PlotInput): Promise<Plot> {
  return requestJson(`${BASE}/plots`, jsonPost(input))
}
/** Retrieve a plot's seasons. */
export function listSeasons(plotId: string, offset = 0): Promise<Page<Season>> {
  const query = new URLSearchParams({ plot_id: plotId, limit: '20', offset: String(offset) })
  return requestJson(`${BASE}/seasons?${query}`)
}
/** Establish a rice season. */
export function createSeason(input: SeasonInput): Promise<Season> {
  return requestJson(`${BASE}/seasons`, jsonPost(input))
}
/** Confirm completion using an actual end date. */
export function closeSeason(seasonId: string, endDate: string): Promise<Season> {
  return requestJson(
    `${BASE}/seasons/${encodeURIComponent(seasonId)}/close`,
    jsonPost({ end_date: endDate }),
  )
}
/** Retrieve current operations or retained revisions with real pagination. */
export function listEvents(
  seasonId: string,
  offset = 0,
  includeHistory = false,
): Promise<Page<ManagementEvent>> {
  const query = new URLSearchParams({
    season_id: seasonId,
    limit: '20',
    offset: String(offset),
    include_history: String(includeHistory),
  })
  return requestJson(`${BASE}/management-events?${query}`)
}
/** Record an operation under one season. */
export function createEvent(seasonId: string, input: EventInput): Promise<ManagementEvent> {
  return requestJson(`${BASE}/management-events`, jsonPost({ season_id: seasonId, ...input }))
}
/** Append a replacement rather than overwriting the old operation. */
export function correctEvent(
  eventId: string,
  input: EventInput,
  reason: string,
): Promise<ManagementEvent> {
  return requestJson(
    `${BASE}/management-events/${encodeURIComponent(eventId)}/corrections`,
    jsonPost({ ...input, correction_reason: reason }),
  )
}
