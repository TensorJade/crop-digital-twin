<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PageNavigation from '../../components/PageNavigation.vue'
import { closeSeason, createSeason } from './api'
import { localDate } from './types'
import type { EstablishmentMethod, Page, Plot, Season } from './types'

const props = defineProps<{
  plot: Plot
  seasons: Page<Season> | null
  selectedId: string | null
  isLoading: boolean
  canManage: boolean
}>()
const emit = defineEmits<{
  select: [id: string]
  saved: [season: Season]
  navigate: [offset: number]
}>()
const isAdding = ref(false)
const isClosing = ref(false)
const isSaving = ref(false)
const error = ref('')
const startDate = ref(localDate())
const endDate = ref(localDate())
const establishment = ref<EstablishmentMethod | ''>('')
const varietyName = ref('')
const selectedSeason = computed(
  () => props.seasons?.items.find((season) => season.id === props.selectedId) ?? null,
)

watch(
  () => props.plot.id,
  () => {
    isAdding.value = false
    isClosing.value = false
    error.value = ''
    varietyName.value = ''
    establishment.value = ''
    startDate.value = localDate()
  },
)
watch(
  () => props.selectedId,
  () => {
    isClosing.value = false
    error.value = ''
  },
)

async function saveSeason() {
  if (!establishment.value || isSaving.value) return
  const plotId = props.plot.id
  isSaving.value = true
  error.value = ''
  try {
    const season = await createSeason({
      plot_id: plotId,
      start_date: startDate.value,
      establishment_method: establishment.value,
      variety_name: varietyName.value.trim() || null,
    })
    if (props.plot.id === plotId) isAdding.value = false
    emit('saved', season)
  } catch (failure) {
    if (props.plot.id === plotId)
      error.value = failure instanceof Error ? failure.message : '种植季保存失败'
  } finally {
    isSaving.value = false
  }
}

async function finishSeason() {
  const season = selectedSeason.value
  if (!season || isSaving.value) return
  isSaving.value = true
  error.value = ''
  try {
    emit('saved', await closeSeason(season.id, endDate.value))
    if (props.selectedId === season.id) isClosing.value = false
  } catch (failure) {
    if (props.selectedId === season.id)
      error.value = failure instanceof Error ? failure.message : '结束种植季失败'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="season-panel surface" aria-labelledby="seasons-title">
    <div class="section-heading">
      <div>
        <p class="step-label">第二步 · {{ plot.name }}</p>
        <h2 id="seasons-title">选择种植季</h2>
      </div>
      <button
        v-if="canManage && seasons?.total !== 0"
        type="button"
        class="secondary-button"
        :disabled="isSaving"
        @click="isAdding = !isAdding"
      >
        {{ isAdding ? '收起' : '建立种植季' }}
      </button>
    </div>
    <p v-if="isLoading" class="muted" role="status">正在读取种植季…</p>
    <div v-else-if="seasons?.items.length" class="season-list">
      <button
        v-for="season in seasons.items"
        :key="season.id"
        type="button"
        class="season-choice"
        :class="{ selected: season.id === selectedId }"
        :aria-pressed="season.id === selectedId"
        @click="emit('select', season.id)"
      >
        <span class="season-label">水稻 · {{ season.variety_name || '品种待补充' }}</span>
        <span class="season-date"
          >{{ season.start_date }} <span aria-hidden="true">→</span>
          {{ season.end_date || '本季进行中' }}</span
        >
        <small
          >{{ season.establishment_method === 'transplanting' ? '移栽' : '直播' }} ·
          {{ season.end_date ? '已结束' : '进行中' }}</small
        >
      </button>
    </div>
    <p v-else-if="seasons" class="empty-guidance">
      为 {{ plot.name }} 建立一季水稻，才能记录这一季的农事。
    </p>
    <PageNavigation
      v-if="seasons"
      v-bind="seasons"
      :disabled="isLoading"
      @navigate="emit('navigate', $event)"
    />
    <form
      v-if="canManage && (isAdding || seasons?.total === 0)"
      class="entry-form"
      @submit.prevent="saveSeason"
    >
      <h3>建立种植季</h3>
      <div class="field-pair">
        <label
          >种植方式<select v-model="establishment" required>
            <option disabled value="">请选择</option>
            <option value="direct_sowing">直播</option>
            <option value="transplanting">移栽</option>
          </select></label
        >
        <label>播种 / 移栽日期<input v-model="startDate" type="date" required /></label>
      </div>
      <label
        >水稻品种（选填）<input
          v-model="varietyName"
          maxlength="100"
          placeholder="填写实际品种名称"
      /></label>
      <button class="primary-button" :disabled="isSaving">
        {{ isSaving ? '保存中…' : '保存种植季' }}
      </button>
    </form>
    <div v-if="canManage && selectedSeason && !selectedSeason.end_date" class="season-actions">
      <button type="button" class="text-button" @click="isClosing = !isClosing">
        {{ isClosing ? '取消结束' : '结束当前种植季' }}
      </button>
      <form v-if="isClosing" class="closing-form" @submit.prevent="finishSeason">
        <label
          >实际结束日期<input
            v-model="endDate"
            type="date"
            required
            :min="selectedSeason.start_date"
        /></label>
        <p class="field-help">结束后仍可补记本季历史农事；结束日期确认后不能直接更改。</p>
        <button class="secondary-button" :disabled="isSaving">确认结束该季</button>
      </form>
    </div>
    <p v-if="error" class="error-message" role="alert">{{ error }}</p>
  </section>
</template>
