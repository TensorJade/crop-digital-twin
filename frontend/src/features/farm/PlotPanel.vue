<script setup lang="ts">
import { ref } from 'vue'
import PageNavigation from '../../components/PageNavigation.vue'
import { createPlot } from './api'
import { displayQuantity } from './types'
import type { Page, Plot } from './types'

defineProps<{ plots: Page<Plot> | null; selectedId: string | null; isLoading: boolean }>()
const emit = defineEmits<{
  select: [id: string]
  created: [plot: Plot]
  navigate: [offset: number]
}>()
const isAdding = ref(false)
const isSaving = ref(false)
const error = ref('')
const plotName = ref('')
const areaMu = ref('')
const latitude = ref('')
const longitude = ref('')

async function savePlot() {
  if (isSaving.value) return
  isSaving.value = true
  error.value = ''
  try {
    const plot = await createPlot({
      name: plotName.value,
      area_mu: Number(areaMu.value),
      latitude: Number(latitude.value),
      longitude: Number(longitude.value),
    })
    plotName.value = ''
    areaMu.value = ''
    latitude.value = ''
    longitude.value = ''
    isAdding.value = false
    emit('created', plot)
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : '地块保存失败'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="plot-panel" aria-labelledby="plots-title">
    <div class="section-heading">
      <div>
        <p class="step-label">第一步</p>
        <h2 id="plots-title">选择地块</h2>
      </div>
      <button
        v-if="plots?.total !== 0"
        type="button"
        class="text-button"
        :disabled="isSaving"
        @click="isAdding = !isAdding"
      >
        {{ isAdding ? '收起' : '登记地块' }}
      </button>
    </div>
    <p v-if="isLoading" class="muted" role="status">正在读取地块…</p>
    <div v-else-if="plots?.items.length" class="plot-list">
      <button
        v-for="plot in plots.items"
        :key="plot.id"
        type="button"
        class="plot-choice"
        :class="{ selected: plot.id === selectedId }"
        :aria-pressed="plot.id === selectedId"
        @click="emit('select', plot.id)"
      >
        <strong>{{ plot.name }}</strong
        ><span>{{ displayQuantity(plot.area_mu) }} 亩</span>
        <small>纬度 {{ plot.latitude.toFixed(4) }} · 经度 {{ plot.longitude.toFixed(4) }}</small>
      </button>
    </div>
    <p v-else-if="plots" class="empty-guidance">先登记第一块田，再建立它的种植季。</p>
    <PageNavigation
      v-if="plots"
      v-bind="plots"
      :disabled="isLoading"
      @navigate="emit('navigate', $event)"
    />
    <form
      v-if="isAdding || plots?.total === 0"
      class="entry-form compact-form"
      @submit.prevent="savePlot"
    >
      <h3>登记地块</h3>
      <label
        >地块名称<input
          v-model="plotName"
          name="plotName"
          required
          maxlength="80"
          placeholder="例如：村东一号田"
      /></label>
      <label
        >面积（亩）<input
          v-model="areaMu"
          name="areaMu"
          type="number"
          required
          min="0.000001"
          max="1000000"
          step="0.000001"
          inputmode="decimal"
          placeholder="填写实际面积"
      /></label>
      <div class="field-pair">
        <label
          >纬度<input
            v-model="latitude"
            name="latitude"
            type="number"
            required
            min="-90"
            max="90"
            step="any"
            inputmode="decimal"
            placeholder="例如 23.1"
        /></label>
        <label
          >经度<input
            v-model="longitude"
            name="longitude"
            type="number"
            required
            min="-180"
            max="180"
            step="any"
            inputmode="decimal"
            placeholder="例如 113.2"
        /></label>
      </div>
      <p class="field-help">填写地块位置的 WGS84 经纬度。地图选点将由地图模块提供。</p>
      <p v-if="error" class="error-message" role="alert">{{ error }}</p>
      <button class="primary-button" :disabled="isSaving">
        {{ isSaving ? '保存中…' : '保存地块' }}
      </button>
    </form>
  </section>
</template>
