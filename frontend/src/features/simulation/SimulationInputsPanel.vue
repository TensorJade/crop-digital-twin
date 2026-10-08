<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Page } from '../../api/types'
import PageNavigation from '../../components/PageNavigation.vue'
import type { Plot, Season } from '../farm/types'
import InputAssetForm from './InputAssetForm.vue'
import { checkInputs, getSnapshot, listAssets, listSnapshots, saveSnapshot } from './api'
import { downloadData } from './files'
import { assetLabels, selectionLabels } from './types'
import type { AssetKind, InputAsset, InputReport, InputSnapshot, SnapshotSelection } from './types'

const props = defineProps<{ plot: Plot; season: Season; canManage: boolean }>()
const kinds: AssetKind[] = ['soil', 'crop', 'weather']
const assets = ref<Record<AssetKind, Page<InputAsset> | null>>({
  soil: null,
  crop: null,
  weather: null,
})
const selected = ref<Record<AssetKind, string>>({ soil: '', crop: '', weather: '' })
const snapshots = ref<Page<InputSnapshot> | null>(null)
const addingKind = ref<AssetKind | null>(null)
const emergenceDate = ref('')
const cutoffDate = ref('')
const report = ref<InputReport | null>(null)
const error = ref('')
const notice = ref('')
const isLoading = ref(false)
const isWorking = ref(false)
const downloadingId = ref('')
let generation = 0
onBeforeUnmount(() => ++generation)
watch(
  [selected, emergenceDate, cutoffDate],
  () => {
    report.value = null
    notice.value = ''
  },
  { deep: true },
)
const canPrepare = computed(
  () => kinds.every((kind) => selected.value[kind]) && emergenceDate.value && cutoffDate.value,
)

async function reload() {
  const requestGeneration = ++generation
  isLoading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    ...kinds.map((kind) => listAssets(kind, props.plot.id)),
    listSnapshots(props.season.id),
  ])
  if (requestGeneration !== generation) return
  results.forEach((result, index) => {
    if (result.status === 'rejected') {
      error.value =
        result.reason instanceof Error ? result.reason.message : '资料读取失败，请重新读取'
      return
    }
    if (index < kinds.length) {
      const kind = kinds[index]!
      const page = result.value as Page<InputAsset>
      assets.value[kind] = page
      if (!page.items.some((item) => item.id === selected.value[kind]))
        selected.value[kind] = page.items[0]?.id || ''
    } else snapshots.value = result.value as Page<InputSnapshot>
  })
  isLoading.value = false
}

async function assetPage(kind: AssetKind, offset: number) {
  const requestGeneration = ++generation
  isLoading.value = true
  error.value = ''
  try {
    const page = await listAssets(kind, props.plot.id, offset)
    if (requestGeneration !== generation) return
    assets.value[kind] = page
    selected.value[kind] = page.items[0]?.id || ''
  } catch (failure) {
    if (requestGeneration === generation)
      error.value = failure instanceof Error ? failure.message : '资料读取失败'
  } finally {
    if (requestGeneration === generation) isLoading.value = false
  }
}

async function snapshotPage(offset: number) {
  const requestGeneration = ++generation
  isLoading.value = true
  error.value = ''
  try {
    const page = await listSnapshots(props.season.id, offset)
    if (requestGeneration === generation) snapshots.value = page
  } catch (failure) {
    if (requestGeneration === generation)
      error.value = failure instanceof Error ? failure.message : '快照读取失败'
  } finally {
    if (requestGeneration === generation) isLoading.value = false
  }
}

async function assetCreated(asset: InputAsset) {
  addingKind.value = null
  await reload()
  selected.value[asset.kind] = asset.id
  notice.value = '资料已保存，旧版本仍可选择。'
}

function selection(): SnapshotSelection {
  return {
    season_id: props.season.id,
    soil_asset_id: selected.value.soil,
    crop_asset_id: selected.value.crop,
    weather_asset_id: selected.value.weather,
    emergence_date: emergenceDate.value,
    cutoff_date: cutoffDate.value,
  }
}

async function prepare(save: boolean) {
  if (isWorking.value || !canPrepare.value) return
  const requestGeneration = generation
  const selectedInput = selection()
  isWorking.value = true
  error.value = ''
  try {
    if (save) {
      const snapshot = await saveSnapshot(selectedInput)
      if (requestGeneration !== generation) return
      report.value = snapshot.report
      notice.value = `输入快照第 ${snapshot.version} 版已保存。`
      const page = await listSnapshots(props.season.id)
      if (requestGeneration === generation) snapshots.value = page
    } else {
      const checked = await checkInputs(selectedInput)
      if (requestGeneration === generation) report.value = checked
    }
  } catch (failure) {
    if (requestGeneration === generation)
      error.value = failure instanceof Error ? failure.message : '检查或保存失败，请重试'
  } finally {
    isWorking.value = false
  }
}

async function downloadSnapshot(snapshot: InputSnapshot) {
  if (downloadingId.value) return
  const requestGeneration = generation
  downloadingId.value = snapshot.id
  error.value = ''
  try {
    const detail = await getSnapshot(snapshot.id)
    if (requestGeneration !== generation) return
    downloadData(
      `rice-input-v${snapshot.version}-${snapshot.id}.json`,
      JSON.stringify(detail, null, 2),
    )
  } catch (failure) {
    if (requestGeneration === generation)
      error.value = failure instanceof Error ? failure.message : '快照下载失败，请重试'
  } finally {
    downloadingId.value = ''
  }
}
onMounted(() => void reload())
</script>

<template>
  <section class="simulation-input-panel" aria-labelledby="simulation-inputs-title">
    <div class="section-heading">
      <div>
        <p class="step-label">为这一季准备资料</p>
        <h2 id="simulation-inputs-title">模拟输入资料</h2>
      </div>
      <span class="local-badge">资料准备</span>
    </div>
    <p class="muted">保存土壤、品种和天气的版本，再检查这一季的资料。生长模拟将在下一阶段接入。</p>
    <p v-if="isLoading" class="muted" role="status">正在读取资料…</p>
    <div v-if="error" class="workspace-error" role="alert">
      <span>{{ error }}</span
      ><button type="button" class="text-button" :disabled="isLoading || isWorking" @click="reload">
        重新读取
      </button>
    </div>
    <div class="input-source-list">
      <div v-for="kind in kinds" :key="kind" class="input-source-row">
        <div>
          <strong>{{ assetLabels[kind] }}</strong>
          <p v-if="!assets[kind]?.total" class="muted">
            {{ canManage ? '尚未准备，先添加资料。' : '尚无资料，请联系管理员补充。' }}
          </p>
        </div>
        <div class="input-source-choice">
          <label v-if="assets[kind]?.items.length"
            >{{ selectionLabels[kind]
            }}<select v-model="selected[kind]" :disabled="isLoading || isWorking">
              <option v-for="asset in assets[kind]?.items" :key="asset.id" :value="asset.id">
                {{ asset.name }}
              </option>
            </select></label
          >
          <p
            v-if="assets[kind]?.items.find((asset) => asset.id === selected[kind])"
            class="input-source-note"
          >
            来源：{{ assets[kind]?.items.find((asset) => asset.id === selected[kind])?.source }}
          </p>
          <PageNavigation
            v-if="assets[kind]"
            v-bind="assets[kind]!"
            :disabled="isLoading || isWorking"
            @navigate="assetPage(kind, $event)"
          />
        </div>
        <button
          v-if="canManage"
          type="button"
          class="text-button"
          :disabled="isLoading || isWorking"
          @click="addingKind = addingKind === kind ? null : kind"
        >
          {{ kind === 'soil' ? '登记土壤' : kind === 'crop' ? '导入品种' : '导入天气' }}
        </button>
      </div>
    </div>
    <InputAssetForm
      v-if="canManage && addingKind"
      :key="addingKind"
      :kind="addingKind"
      :plot-id="plot.id"
      @created="assetCreated"
      @cancel="addingKind = null"
    />
    <form v-if="canManage" class="entry-form input-period-form" @submit.prevent="prepare(false)">
      <h3>检查这一季的输入</h3>
      <div class="field-pair">
        <label
          >实际出苗日期<input
            v-model="emergenceDate"
            type="date"
            required
            :disabled="isWorking" /></label
        ><label
          >资料截止日期<input v-model="cutoffDate" type="date" required :disabled="isWorking"
        /></label>
      </div>
      <p class="muted">出苗日期按实际记录填写，不能直接用播种或移栽日期代替。</p>
      <div class="form-actions">
        <button class="primary-button" :disabled="!canPrepare || isWorking || isLoading">
          {{ isWorking ? '处理中…' : '检查输入资料' }}</button
        ><button
          type="button"
          class="secondary-button"
          :disabled="!canPrepare || isWorking || isLoading"
          @click="prepare(true)"
        >
          保存输入快照
        </button>
      </div>
    </form>
    <p v-if="notice" class="input-notice" role="status">{{ notice }}</p>
    <div v-if="report" class="input-report" aria-label="输入检查结果">
      <strong>{{ report.input_ready ? '输入完整性检查通过' : '还有资料需要补齐或核对' }}</strong>
      <ul v-if="report.blocking_issues.length">
        <li v-for="issue in report.blocking_issues" :key="issue.code">
          {{
            issue.code === 'MISSING_PARAMETERS'
              ? '品种参数不完整，请联系参数提供者补充。'
              : issue.message
          }}
        </li>
      </ul>
      <p class="muted">当前保存的是输入资料，尚未运行作物模型。</p>
      <details v-if="report.missing_parameters.length">
        <summary>查看缺少的参数</summary>
        <p class="input-source-note">{{ report.missing_parameters.join(', ') }}</p>
      </details>
      <details>
        <summary>查看适用条件</summary>
        <ul>
          <li v-for="issue in report.warnings" :key="issue.code">{{ issue.message }}</li>
        </ul>
      </details>
    </div>
    <div class="input-history">
      <h3>已保存的输入版本</h3>
      <p v-if="snapshots?.total === 0" class="empty-guidance">
        还没有快照。保存后可查看或下载同一季的历史资料。
      </p>
      <article v-for="snapshot in snapshots?.items" :key="snapshot.id" class="input-snapshot-row">
        <div>
          <strong>第 {{ snapshot.version }} 版</strong
          ><span>{{ snapshot.report.input_ready ? '输入完整' : '待补齐或核对' }}</span
          ><small>{{ new Date(snapshot.created_at).toLocaleString('zh-CN') }}</small>
        </div>
        <button
          type="button"
          class="text-button"
          :disabled="!!downloadingId"
          @click="downloadSnapshot(snapshot)"
        >
          下载第 {{ snapshot.version }} 版
        </button>
      </article>
      <PageNavigation
        v-if="snapshots"
        v-bind="snapshots"
        :disabled="isLoading || isWorking"
        @navigate="snapshotPage"
      />
    </div>
  </section>
</template>
