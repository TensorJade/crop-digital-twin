<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Identity } from '../features/identity/types'
import PlotPanel from '../features/farm/PlotPanel.vue'
import SeasonPanel from '../features/farm/SeasonPanel.vue'
import ManagementPanel from '../features/farm/ManagementPanel.vue'
import SimulationInputsPanel from '../features/simulation/SimulationInputsPanel.vue'
import SimulationRunsPanel from '../features/simulation/SimulationRunsPanel.vue'
import { useFarmWorkspace } from '../features/farm/useFarmWorkspace'

const props = defineProps<{ identity: Identity }>()
const canManage = computed(() => props.identity.user.role !== 'viewer')

const {
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
} = useFarmWorkspace()
const seasonView = ref<'management' | 'inputs' | 'runs'>('management')
watch(selectedSeasonId, () => {
  seasonView.value = 'management'
})
</script>

<template>
  <div class="farm-workspace">
    <header class="workspace-header">
      <div>
        <p class="brand-label">华南水稻 · 农田管理</p>
        <h1>我的农田</h1>
        <p class="workspace-intro">选一块田，记录这一季。</p>
      </div>
      <span class="local-badge">{{ canManage ? '农田管理' : '仅查看' }}</span>
    </header>
    <div v-if="error" class="workspace-error" role="alert">
      <span>{{ error }}</span
      ><button type="button" class="text-button" @click="loadPlots()">重新读取</button>
    </div>
    <main class="farm-layout">
      <aside class="field-sidebar">
        <PlotPanel
          :can-manage="canManage"
          :plots="plots"
          :selected-id="selectedPlotId"
          :is-loading="isLoadingPlots"
          @select="selectPlot"
          @created="loadPlots(0, $event.id)"
          @navigate="loadPlots($event)"
        />
      </aside>
      <div class="field-content">
        <template v-if="selectedPlot">
          <SeasonPanel
            :can-manage="canManage"
            :plot="selectedPlot"
            :seasons="seasons"
            :selected-id="selectedSeasonId"
            :is-loading="isLoadingSeasons"
            @select="selectedSeasonId = $event"
            @saved="seasonSaved"
            @navigate="loadSeasons($event)"
          />
          <template v-if="selectedSeason">
            <nav class="season-tabs" aria-label="本季资料">
              <button
                type="button"
                :aria-pressed="seasonView === 'management'"
                @click="seasonView = 'management'"
              >
                农事记录
              </button>
              <button
                type="button"
                :aria-pressed="seasonView === 'inputs'"
                @click="seasonView = 'inputs'"
              >
                模拟资料
              </button>
              <button
                type="button"
                :aria-pressed="seasonView === 'runs'"
                @click="seasonView = 'runs'"
              >
                生长计算
              </button>
            </nav>
            <ManagementPanel
              v-if="seasonView === 'management'"
              :key="selectedSeason.id"
              :season="selectedSeason"
              :can-manage="canManage"
            />
            <SimulationInputsPanel
              v-else-if="seasonView === 'inputs'"
              :key="selectedSeason.id"
              :season="selectedSeason"
              :plot="selectedPlot"
              :can-manage="canManage"
            />
            <SimulationRunsPanel
              v-else
              :key="selectedSeason.id"
              :season="selectedSeason"
              :can-manage="canManage"
            />
          </template>
        </template>
        <section v-else class="onboarding-surface">
          <p class="step-label">从一块田开始</p>
          <h2>把农田和管理记录放在一起</h2>
          <p>
            {{
              canManage
                ? '登记位置和面积，建立种植季，再记录每次实际管理。'
                : '本组织还没有地块，请联系管理员登记。'
            }}
          </p>
          <ol v-if="canManage" class="onboarding-steps">
            <li><strong>地块</strong><span>这块田在哪里、多大</span></li>
            <li><strong>种植季</strong><span>什么时候播种或移栽</span></li>
            <li><strong>农事</strong><span>这一天做了哪些管理</span></li>
          </ol>
        </section>
      </div>
    </main>
    <footer class="workspace-footer">
      当前支持农田记录、模拟资料与潜在生长计算。地图和遥感将按模块接入。
    </footer>
  </div>
</template>
