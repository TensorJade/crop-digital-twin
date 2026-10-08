import { computed, onMounted, ref } from 'vue'
import { listPlots, listSeasons } from './api'
import type { Page, Plot, Season } from './types'

/** Orchestrate local selection; generation checks prevent stale responses from replacing a new plot. */
export function useFarmWorkspace() {
  const plots = ref<Page<Plot> | null>(null)
  const seasons = ref<Page<Season> | null>(null)
  const selectedPlotId = ref<string | null>(null)
  const selectedSeasonId = ref<string | null>(null)
  const isLoadingPlots = ref(false)
  const isLoadingSeasons = ref(false)
  const error = ref('')
  let plotGeneration = 0
  let seasonGeneration = 0

  const selectedPlot = computed(
    () => plots.value?.items.find((plot) => plot.id === selectedPlotId.value) ?? null,
  )
  const selectedSeason = computed(
    () => seasons.value?.items.find((season) => season.id === selectedSeasonId.value) ?? null,
  )

  async function loadSeasons(offset = 0, preferredId?: string) {
    const plotId = selectedPlotId.value
    const generation = ++seasonGeneration
    if (!plotId) return
    isLoadingSeasons.value = true
    try {
      const page = await listSeasons(plotId, offset)
      if (generation !== seasonGeneration || plotId !== selectedPlotId.value) return
      seasons.value = page
      const candidate = preferredId ?? selectedSeasonId.value
      selectedSeasonId.value =
        page.items.find((season) => season.id === candidate)?.id ?? page.items[0]?.id ?? null
      error.value = ''
    } catch (failure) {
      if (generation === seasonGeneration)
        error.value = failure instanceof Error ? failure.message : '种植季读取失败'
    } finally {
      if (generation === seasonGeneration) isLoadingSeasons.value = false
    }
  }

  async function selectPlot(plotId: string) {
    ++seasonGeneration
    selectedPlotId.value = plotId
    selectedSeasonId.value = null
    seasons.value = null
    await loadSeasons()
  }

  async function loadPlots(offset = 0, preferredId?: string) {
    const generation = ++plotGeneration
    isLoadingPlots.value = true
    try {
      const page = await listPlots(offset)
      if (generation !== plotGeneration) return
      plots.value = page
      const candidate = preferredId ?? selectedPlotId.value
      const selection =
        page.items.find((plot) => plot.id === candidate)?.id ?? page.items[0]?.id ?? null
      error.value = ''
      if (selection !== selectedPlotId.value) {
        if (selection) await selectPlot(selection)
        else {
          selectedPlotId.value = null
          selectedSeasonId.value = null
          seasons.value = null
          ++seasonGeneration
          isLoadingSeasons.value = false
        }
      } else if (selection) await loadSeasons(seasons.value?.offset ?? 0)
    } catch (failure) {
      if (generation === plotGeneration)
        error.value = failure instanceof Error ? failure.message : '地块读取失败'
    } finally {
      if (generation === plotGeneration) isLoadingPlots.value = false
    }
  }

  function seasonSaved(season: Season) {
    if (season.plot_id === selectedPlotId.value) void loadSeasons(0, season.id)
  }

  onMounted(() => {
    void loadPlots()
  })
  return {
    plots,
    seasons,
    selectedPlotId,
    selectedSeasonId,
    selectedPlot,
    selectedSeason,
    isLoadingPlots,
    isLoadingSeasons,
    error,
    loadPlots,
    loadSeasons,
    selectPlot,
    seasonSaved,
  }
}
