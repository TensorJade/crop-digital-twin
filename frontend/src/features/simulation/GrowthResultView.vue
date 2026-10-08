<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { GrowthDay, GrowthResult } from './runTypes'

const props = defineProps<{ result: GrowthResult }>()
const index = ref(0)
const metric = ref<'lai' | 'above_ground_kg_ha'>('lai')
watch(
  () => props.result,
  () => {
    index.value = props.result.daily.length - 1
  },
  { immediate: true },
)
const selected = computed(() => props.result.daily[index.value] || props.result.daily[0]!)
const metricLabel = computed(() =>
  metric.value === 'lai' ? '叶面积指数' : '地上部干物质（kg/公顷）',
)
const maximum = computed(() => Math.max(1, ...props.result.daily.map((day) => day[metric.value])))
const points = computed(() =>
  props.result.daily
    .map(
      (day, i) =>
        `${35 + (i / Math.max(1, props.result.daily.length - 1)) * 630},${205 - (day[metric.value] / maximum.value) * 170}`,
    )
    .join(' '),
)
function number(value: number) {
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}
function stage(day: GrowthDay) {
  return day.dvs < 1 ? '营养生长' : day.dvs < 2 ? '生殖生长' : '达到成熟参数范围'
}
</script>

<template>
  <section class="growth-result" aria-label="逐日潜在生长结果">
    <div class="section-heading">
      <div>
        <p class="step-label">已计算的生长轨迹</p>
        <h3>潜在生长 · {{ selected.date }}</h3>
      </div>
      <span class="local-badge">{{ stage(selected) }}</span>
    </div>
    <div class="growth-values">
      <p>
        <small>叶面积指数</small><strong>{{ number(selected.lai) }}</strong
        ><span>m²/m²</span>
      </p>
      <p>
        <small>地上部干物质</small><strong>{{ number(selected.above_ground_kg_ha) }}</strong
        ><span>kg/公顷</span>
      </p>
      <p>
        <small>贮藏器官干物质</small><strong>{{ number(selected.storage_organs_kg_ha) }}</strong
        ><span>kg/公顷</span>
      </p>
    </div>
    <label class="growth-date-control"
      >查看日期<input
        v-model.number="index"
        type="range"
        min="0"
        :max="result.daily.length - 1"
        step="1"
        :disabled="result.daily.length === 1"
    /></label>
    <label class="growth-metric"
      >曲线指标<select v-model="metric">
        <option value="lai">叶面积指数</option>
        <option value="above_ground_kg_ha">地上部干物质</option>
      </select></label
    >
    <svg
      class="growth-chart"
      viewBox="0 0 700 250"
      role="img"
      :aria-label="metricLabel + '逐日曲线'"
    >
      <line
        v-for="y in [35, 120, 205]"
        :key="y"
        x1="35"
        :y1="y"
        x2="665"
        :y2="y"
        class="growth-grid"
      />
      <polyline :points="points" class="growth-line" />
      <circle
        :cx="35 + (index / Math.max(1, result.daily.length - 1)) * 630"
        :cy="205 - (selected[metric] / maximum) * 170"
        r="5"
        class="growth-point"
      />
      <text x="35" y="25">{{ number(maximum) }}</text>
      <text x="35" y="235">{{ result.daily[0]?.date }}</text>
      <text x="665" y="235" text-anchor="end">{{ result.last_crop_date }}</text>
    </svg>
    <p class="muted">这是水肥充足条件下的模型计算，贮藏器官干物质不能直接当作实收稻谷产量。</p>
    <details>
      <summary>查看逐日数值与适用条件</summary>
      <ul>
        <li v-for="item in result.assumptions" :key="item">{{ item }}</li>
      </ul>
      <p class="muted">
        {{ result.model_code }} · PCSE {{ result.pcse_version }} · 参数尚未通过当地实测验证
      </p>
      <div class="growth-table-scroll">
        <table class="growth-table">
          <caption>
            逐日模型结果
          </caption>
          <thead>
            <tr>
              <th>日期</th>
              <th>发育进度</th>
              <th>叶面积指数</th>
              <th>地上部干物质 kg/公顷</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in result.daily" :key="day.date">
              <td>{{ day.date }}</td>
              <td>{{ number(day.dvs) }}</td>
              <td>{{ number(day.lai) }}</td>
              <td>{{ number(day.above_ground_kg_ha) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </section>
</template>
