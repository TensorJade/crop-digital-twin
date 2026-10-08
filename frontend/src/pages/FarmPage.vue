<script setup lang="ts">
import PlotPanel from '../features/farm/PlotPanel.vue'
import SeasonPanel from '../features/farm/SeasonPanel.vue'
import ManagementPanel from '../features/farm/ManagementPanel.vue'
import { useFarmWorkspace } from '../features/farm/useFarmWorkspace'

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
</script>

<template>
  <div class="farm-workspace">
    <header class="workspace-header">
      <div>
        <p class="brand-label">华南水稻 · 农田管理</p>
        <h1>我的农田</h1>
        <p class="workspace-intro">选一块田，记录这一季。</p>
      </div>
      <span class="local-badge">本地试用</span>
    </header>
    <div v-if="error" class="workspace-error" role="alert">
      <span>{{ error }}</span
      ><button type="button" class="text-button" @click="loadPlots()">重新读取</button>
    </div>
    <main class="farm-layout">
      <aside class="field-sidebar">
        <PlotPanel
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
            :plot="selectedPlot"
            :seasons="seasons"
            :selected-id="selectedSeasonId"
            :is-loading="isLoadingSeasons"
            @select="selectedSeasonId = $event"
            @saved="seasonSaved"
            @navigate="loadSeasons($event)"
          />
          <ManagementPanel v-if="selectedSeason" :season="selectedSeason" />
        </template>
        <section v-else class="onboarding-surface">
          <p class="step-label">从一块田开始</p>
          <h2>把农田和管理记录放在一起</h2>
          <p>登记位置和面积，建立种植季，再记录每次实际管理。</p>
          <ol class="onboarding-steps">
            <li><strong>地块</strong><span>这块田在哪里、多大</span></li>
            <li><strong>种植季</strong><span>什么时候播种或移栽</span></li>
            <li><strong>农事</strong><span>这一天做了哪些管理</span></li>
          </ol>
        </section>
      </div>
    </main>
    <footer class="workspace-footer">
      当前支持农田与农事记录。地图、生长模拟和遥感观测将按模块接入。
    </footer>
  </div>
</template>
