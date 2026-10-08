<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { createAsset } from './api'
import { downloadData, parseCropFile, readInputFile, weatherHeader } from './files'
import { assetLabels } from './types'
import type { AssetKind, InputAsset } from './types'

const props = defineProps<{ kind: AssetKind; plotId: string }>()
const emit = defineEmits<{ created: [asset: InputAsset]; cancel: [] }>()
const name = ref('')
const source = ref('')
const sourceLicense = ref('')
const wilting = ref('')
const capacity = ref('')
const saturation = ref('')
const depth = ref('')
const sampledOn = ref('')
const weatherKind = ref<'station' | 'gridded'>('station')
const stationId = ref('')
const latitude = ref('')
const longitude = ref('')
const elevation = ref('')
const timeBasis = ref<'Asia/Shanghai' | 'UTC' | 'LST'>('Asia/Shanghai')
const angstromA = ref('')
const angstromB = ref('')
const file = ref<File | null>(null)
const error = ref('')
const isSaving = ref(false)
let generation = 0
onBeforeUnmount(() => ++generation)

function fileSelected(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
  error.value = ''
}

async function saveAsset() {
  if (isSaving.value) return
  const requestGeneration = ++generation
  isSaving.value = true
  error.value = ''
  try {
    let data: Record<string, unknown>
    if (props.kind === 'soil')
      data = {
        wilting_point: Number(wilting.value),
        field_capacity: Number(capacity.value),
        saturation: Number(saturation.value),
        depth_cm: Number(depth.value),
        sampled_on: sampledOn.value || null,
      }
    else {
      if (!file.value) throw new Error('请选择要导入的资料文件')
      const text = await readInputFile(file.value)
      if (requestGeneration !== generation) return
      data =
        props.kind === 'crop'
          ? parseCropFile(text)
          : {
              source_kind: weatherKind.value,
              station_id: weatherKind.value === 'station' ? stationId.value : null,
              latitude: Number(latitude.value),
              longitude: Number(longitude.value),
              elevation_m: Number(elevation.value),
              wind_height_m: 2,
              time_basis: timeBasis.value,
              angstrom_a: angstromA.value ? Number(angstromA.value) : null,
              angstrom_b: angstromB.value ? Number(angstromB.value) : null,
              csv_text: text,
            }
    }
    const asset = await createAsset({
      kind: props.kind,
      plot_id: props.kind === 'crop' ? null : props.plotId,
      name: name.value,
      source: source.value,
      source_license: sourceLicense.value,
      data,
    })
    if (requestGeneration === generation) emit('created', asset)
  } catch (failure) {
    if (requestGeneration === generation)
      error.value = failure instanceof Error ? failure.message : '资料保存失败，请重试'
  } finally {
    if (requestGeneration === generation) isSaving.value = false
  }
}
</script>

<template>
  <form class="entry-form input-asset-form" @submit.prevent="saveAsset">
    <h3>{{ kind === 'soil' ? '登记' : '导入' }}{{ assetLabels[kind] }}</h3>
    <p class="muted">
      {{
        kind === 'soil'
          ? '按检测报告填写，没有资料时请联系管理员补充。'
          : kind === 'crop'
            ? '使用农艺人员提供的参数文件；保存时不会证明当地适用性。'
            : '导入已发生的逐日天气，缺测留待补齐。'
      }}
    </p>
    <label
      >资料名称<input v-model="name" required maxlength="100" placeholder="便于再次选择的名称"
    /></label>
    <div v-if="kind === 'soil'" class="input-grid">
      <label
        >萎蔫点（体积比）<input
          v-model="wilting"
          type="number"
          required
          min="0"
          max="1"
          step="any"
          inputmode="decimal"
      /></label>
      <label
        >田间持水量（体积比）<input
          v-model="capacity"
          type="number"
          required
          min="0"
          max="1"
          step="any"
          inputmode="decimal"
      /></label>
      <label
        >饱和含水量（体积比）<input
          v-model="saturation"
          type="number"
          required
          min="0"
          max="1"
          step="any"
          inputmode="decimal"
      /></label>
      <label
        >土层深度（cm）<input
          v-model="depth"
          type="number"
          required
          min="0.01"
          max="500"
          step="any"
          inputmode="decimal"
      /></label>
      <label>采样日期（可选）<input v-model="sampledOn" type="date" /></label>
    </div>
    <template v-else>
      <label
        >{{ kind === 'crop' ? '品种参数文件（JSON）' : '逐日天气文件（CSV）'
        }}<input
          type="file"
          :accept="kind === 'crop' ? '.json' : '.csv'"
          required
          @change="fileSelected"
      /></label>
      <template v-if="kind === 'weather'">
        <button
          type="button"
          class="text-button"
          @click="downloadData('weather-columns.csv', weatherHeader + '\n', 'text/csv')"
        >
          下载天气空表
        </button>
        <p class="muted">
          温度 °C，雨量 mm，辐射 MJ/m²，2m 风速 m/s，实际蒸汽压 kPa；最多 366
          天。相对湿度不能直接填入蒸汽压列。
        </p>
        <div class="input-grid">
          <label
            >天气来源类型<select v-model="weatherKind">
              <option value="station">气象站观测</option>
              <option value="gridded">网格天气数据</option>
            </select></label
          >
          <label v-if="weatherKind === 'station'"
            >气象站编号<input v-model="stationId" required maxlength="80"
          /></label>
          <label
            >天气来源纬度<input
              v-model="latitude"
              type="number"
              required
              min="-90"
              max="90"
              step="any"
          /></label>
          <label
            >天气来源经度<input
              v-model="longitude"
              type="number"
              required
              min="-180"
              max="180"
              step="any"
          /></label>
          <label
            >天气来源海拔（m）<input
              v-model="elevation"
              type="number"
              required
              min="-500"
              max="9000"
              step="any"
          /></label>
          <label
            >天气日期采用<select v-model="timeBasis">
              <option value="Asia/Shanghai">北京时间</option>
              <option value="UTC">世界时 UTC</option>
              <option value="LST">当地太阳时 LST</option>
            </select></label
          >
        </div>
        <details>
          <summary>模型计算资料（由资料提供者填写）</summary>
          <p class="muted">运行模型需要蒸散计算系数 A/B。没有依据时留空，补齐后另存资料。</p>
          <div class="field-pair">
            <label
              >蒸散计算系数 A<input
                v-model="angstromA"
                type="number"
                min="0.1"
                max="0.4"
                step="any"
            /></label>
            <label
              >蒸散计算系数 B<input
                v-model="angstromB"
                type="number"
                min="0.3"
                max="0.7"
                step="any"
            /></label>
          </div>
        </details>
      </template>
    </template>
    <label
      >资料来源<input
        v-model="source"
        required
        maxlength="1000"
        placeholder="报告编号、提供单位或数据产品及版本"
    /></label>
    <label
      >使用许可说明<input
        v-model="sourceLicense"
        required
        maxlength="300"
        placeholder="如：自有资料，可供本组织使用"
    /></label>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="form-actions">
      <button class="primary-button" :disabled="isSaving">
        {{ isSaving ? '保存中…' : '保存资料' }}
      </button>
      <button type="button" class="text-button" :disabled="isSaving" @click="emit('cancel')">
        取消
      </button>
    </div>
  </form>
</template>
