<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import type { Plot, Season } from '../farm/types'
import { createAsset } from './api'
import { downloadData } from './files'
import type { InputAsset } from './types'
import { nearbyStations, previewWeather } from './weatherApi'
import type { StationList, WeatherPreview } from './weatherApi'

const props = defineProps<{ plot: Plot; season: Season }>()
const emit = defineEmits<{ created: [asset: InputAsset]; cancel: [] }>()
const start = ref(props.season.start_date)
const end = ref('')
const preview = ref<WeatherPreview | null>(null)
const stations = ref<StationList | null>(null)
const error = ref('')
const stationError = ref('')
const isFetching = ref(false)
const isSaving = ref(false)
const isFinding = ref(false)
const angstromA = ref('')
const angstromB = ref('')
let generation = 0
let stationGeneration = 0
onBeforeUnmount(() => {
  ++generation
  ++stationGeneration
})
watch([start, end], () => {
  ++generation
  preview.value = null
  error.value = ''
  isFetching.value = false
})
async function fetchWeather() {
  if (isFetching.value || isSaving.value) return
  const current = ++generation
  isFetching.value = true
  preview.value = null
  error.value = ''
  try {
    const result = await previewWeather(props.plot.id, start.value, end.value)
    if (current === generation) preview.value = result
  } catch (failure) {
    if (current === generation)
      error.value = failure instanceof Error ? failure.message : '天气读取失败，请重试'
  } finally {
    if (current === generation) isFetching.value = false
  }
}
async function findStations() {
  if (isFinding.value) return
  const current = ++stationGeneration
  isFinding.value = true
  stationError.value = ''
  try {
    const result = await nearbyStations(props.plot.id)
    if (current === stationGeneration) stations.value = result
  } catch (failure) {
    if (current === stationGeneration)
      stationError.value = failure instanceof Error ? failure.message : '站点目录读取失败'
  } finally {
    if (current === stationGeneration) isFinding.value = false
  }
}
async function save() {
  if (!preview.value || isSaving.value) return
  const current = generation
  isSaving.value = true
  error.value = ''
  try {
    const asset = await createAsset({
      ...preview.value.asset,
      data: {
        ...preview.value.asset.data,
        angstrom_a: angstromA.value ? Number(angstromA.value) : null,
        angstrom_b: angstromB.value ? Number(angstromB.value) : null,
      },
    })
    if (current === generation) emit('created', asset)
  } catch (failure) {
    if (current === generation)
      error.value = failure instanceof Error ? failure.message : '保存失败，请重试'
  } finally {
    if (current === generation) isSaving.value = false
  }
}
function download() {
  if (preview.value)
    downloadData(
      'nasa-weather-' + start.value + '-' + end.value + '.csv',
      String(preview.value.asset.data.csv_text),
      'text/csv',
    )
}
</script>

<template>
  <section class="weather-source-panel" aria-label="联网获取天气">
    <div class="section-heading">
      <div>
        <p class="step-label">按农田位置准备天气</p>
        <h3>获取历史网格天气</h3>
      </div>
      <button type="button" class="text-button" :disabled="isSaving" @click="emit('cancel')">
        收起
      </button>
    </div>
    <p class="muted">
      按此地块坐标请求 NASA POWER。资料来自卫星与气象模型，保存时会保留原始小时资料和来源。
    </p>
    <form class="entry-form" @submit.prevent="fetchWeather">
      <div class="field-pair">
        <label
          >天气起始日期<input
            v-model="start"
            type="date"
            required
            :disabled="isFetching || isSaving"
        /></label>
        <label
          >天气结束日期<input v-model="end" type="date" required :disabled="isFetching || isSaving"
        /></label>
      </div>
      <p class="muted">
        选择已结束的日期，最多366天；系统会按不超过120天的区间分段获取，近期资料通常延迟数日。
      </p>
      <div class="form-actions">
        <button class="primary-button" :disabled="!start || !end || isFetching || isSaving">
          {{ isFetching ? '正在获取天气…' : '获取并预览天气' }}
        </button>
      </div>
    </form>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <section v-if="preview" class="weather-preview" aria-label="网格天气预览">
      <strong>{{ preview.day_count }}天资料已获取 · 北京时间</strong>
      <p class="input-source-note">{{ preview.asset.source }}</p>
      <div class="growth-table-scroll">
        <table class="growth-table">
          <caption>
            前五日天气预览
          </caption>
          <thead>
            <tr>
              <th>日期</th>
              <th>最低/最高温 ℃</th>
              <th>降水 mm</th>
              <th>辐射 MJ/m²</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in preview.sample_days" :key="day.date">
              <td>{{ day.date }}</td>
              <td>{{ day.tmin_c }} / {{ day.tmax_c }}</td>
              <td>{{ day.rain_mm }}</td>
              <td>{{ day.radiation_mj_m2 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <details>
        <summary>查看来源与适用条件</summary>
        <ul>
          <li v-for="warning in preview.warnings" :key="warning">{{ warning }}</li>
        </ul>
        <p class="input-source-note">{{ preview.asset.source_license }}</p>
      </details>
      <form class="entry-form" @submit.prevent="save">
        <details>
          <summary>模型计算资料（可稍后补齐）</summary>
          <p class="muted">
            由资料提供者填写蒸散计算系数；留空可以保存天气，补齐后另存资料才能计算。
          </p>
          <div class="field-pair">
            <label
              >Angstrom A<input
                v-model="angstromA"
                type="number"
                min="0.1"
                max="0.4"
                step="any"
                :disabled="isSaving"
            /></label>
            <label
              >Angstrom B<input
                v-model="angstromB"
                type="number"
                min="0.3"
                max="0.7"
                step="any"
                :disabled="isSaving"
            /></label>
          </div>
        </details>
        <div class="form-actions">
          <button class="primary-button" :disabled="isSaving">
            {{ isSaving ? '保存中…' : '保存为本地天气资料' }}</button
          ><button type="button" class="secondary-button" @click="download">下载逐日CSV</button>
        </div>
      </form>
    </section>
    <div class="weather-stations">
      <h3>附近的气象站目录</h3>
      <p class="muted">
        查询 NOAA 公开目录中200公里内的最近站点，仅提供位置候选。网格天气和站点观测分别管理。
      </p>
      <button type="button" class="secondary-button" :disabled="isFinding" @click="findStations">
        {{ isFinding ? '正在查询站点…' : '查找附近气象站' }}
      </button>
      <p v-if="stationError" class="form-error" role="alert">{{ stationError }}</p>
      <template v-if="stations">
        <p class="muted">{{ stations.notice }}</p>
        <p v-if="stations.stations.length === 0" class="empty-guidance">
          目录中未找到200公里内的有效位置，仍可获取网格天气或导入已有站点CSV。
        </p>
        <article
          v-for="station in stations.stations"
          :key="station.station_id"
          class="weather-station-row"
        >
          <div>
            <strong>{{ station.name }}</strong
            ><small>{{ station.station_id }} · 距地块约{{ station.distance_km }}公里</small
            ><small>目录覆盖：{{ station.coverage_start }}—{{ station.coverage_end }}</small>
          </div>
          <span class="local-badge">观测尚未接入</span>
        </article>
      </template>
    </div>
  </section>
</template>
