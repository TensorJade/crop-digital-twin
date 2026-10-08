<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Page } from '../../api/types'
import PageNavigation from '../../components/PageNavigation.vue'
import type { Season } from '../farm/types'
import { listSnapshots } from './api'
import { downloadData } from './files'
import GrowthResultView from './GrowthResultView.vue'
import { createRun, getRun, listRuns } from './runApi'
import { failureLabels, runLabels } from './runTypes'
import type { RunDetail, RunSummary } from './runTypes'
import type { InputSnapshot } from './types'

const props = defineProps<{ season: Season; canManage: boolean }>()
const inputs = ref<Page<InputSnapshot> | null>(null)
const runs = ref<Page<RunSummary> | null>(null)
const selectedInput = ref('')
const acknowledged = ref(false)
const active = ref<RunDetail | null>(null)
const error = ref('')
const isLoading = ref(false)
const isQueuing = ref(false)
let requestKey = ''
let lifetime = 0
let detailRequest = 0
let timer: ReturnType<typeof setTimeout> | undefined
onBeforeUnmount(() => {
  ++lifetime
  ++detailRequest
  clearTimeout(timer)
})
watch(selectedInput, () => {
  requestKey = ''
  acknowledged.value = false
})

async function reload() {
  const generation = lifetime
  isLoading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    listSnapshots(props.season.id),
    listRuns(props.season.id),
  ])
  if (generation !== lifetime) return
  const [inputResult, runResult] = results
  if (inputResult!.status === 'fulfilled') {
    inputs.value = inputResult!.value as Page<InputSnapshot>
    if (!inputs.value.items.some((item) => item.id === selectedInput.value))
      selectedInput.value =
        inputs.value.items.find((item) => item.report.simulation_available)?.id || ''
  } else
    error.value =
      inputResult!.reason instanceof Error ? inputResult!.reason.message : '输入读取失败'
  if (runResult!.status === 'fulfilled') {
    runs.value = runResult!.value as Page<RunSummary>
    if (active.value) void view(active.value.id)
    else if (runs.value.items[0]) void view(runs.value.items[0].id)
  } else
    error.value = runResult!.reason instanceof Error ? runResult!.reason.message : '任务读取失败'
  isLoading.value = false
}

async function inputPage(offset: number) {
  const generation = lifetime
  try {
    const page = await listSnapshots(props.season.id, offset)
    if (generation !== lifetime) return
    inputs.value = page
    selectedInput.value = page.items.find((item) => item.report.simulation_available)?.id || ''
  } catch (failure) {
    if (generation === lifetime)
      error.value = failure instanceof Error ? failure.message : '输入读取失败'
  }
}
async function runPage(offset: number) {
  const generation = lifetime
  try {
    const page = await listRuns(props.season.id, offset)
    if (generation === lifetime) runs.value = page
  } catch (failure) {
    if (generation === lifetime)
      error.value = failure instanceof Error ? failure.message : '任务读取失败'
  }
}
async function view(id: string) {
  const generation = ++detailRequest
  clearTimeout(timer)
  try {
    const detail = await getRun(id)
    if (generation !== detailRequest) return
    active.value = detail
    const item = runs.value?.items.find((run) => run.id === id)
    if (item)
      Object.assign(item, {
        status: detail.status,
        attempts: detail.attempts,
        finished_at: detail.finished_at,
        error_code: detail.error_code,
        result_hash: detail.result_hash,
      })
    if (detail.status === 'queued' || detail.status === 'running')
      timer = setTimeout(() => void view(id), 2000)
  } catch (failure) {
    if (generation === detailRequest)
      error.value = failure instanceof Error ? failure.message : '结果读取失败，请刷新'
  }
}
async function queue() {
  if (isQueuing.value || !selectedInput.value || !acknowledged.value) return
  const generation = lifetime
  isQueuing.value = true
  error.value = ''
  requestKey ||= crypto.randomUUID()
  try {
    const created = await createRun(selectedInput.value, requestKey)
    if (generation !== lifetime) return
    requestKey = ''
    active.value = { ...created, result: null }
    void view(created.id)
    const page = await listRuns(props.season.id)
    if (generation === lifetime) runs.value = page
  } catch (failure) {
    if (generation === lifetime)
      error.value = failure instanceof Error ? failure.message : '任务提交失败，请重试'
  } finally {
    isQueuing.value = false
  }
}
function download() {
  if (!active.value?.result) return
  downloadData(
    'rice-growth-' + active.value.id + '.json',
    JSON.stringify(
      {
        id: active.value.id,
        input_id: active.value.input_id,
        input_hash: active.value.input_hash,
        created_at: active.value.created_at,
        payload: active.value.result,
        content_hash: active.value.result_hash,
      },
      null,
      2,
    ),
  )
}
onMounted(() => void reload())
</script>

<template>
  <section class="simulation-run-panel" aria-labelledby="growth-runs-title">
    <div class="section-heading">
      <div>
        <p class="step-label">查看这一季的模型轨迹</p>
        <h2 id="growth-runs-title">潜在生长计算</h2>
      </div>
      <button type="button" class="text-button" :disabled="isLoading || isQueuing" @click="reload">
        刷新资料
      </button>
    </div>
    <p class="muted">
      使用已保存的输入快照，计算水肥充足条件下的逐日生长。模型尚未考虑这一季的灌溉、施肥或病虫害影响。
    </p>
    <p v-if="isLoading" class="muted" role="status">正在读取…</p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <form v-if="canManage" class="entry-form run-start-form" @submit.prevent="queue">
      <label
        >用于计算的输入快照<select
          v-model="selectedInput"
          required
          :disabled="isLoading || isQueuing"
        >
          <option value="">先在模拟资料补齐并保存可计算快照</option>
          <option
            v-for="input in inputs?.items"
            :key="input.id"
            :value="input.id"
            :disabled="!input.report.simulation_available"
          >
            第 {{ input.version }} 版 ·
            {{ input.report.simulation_available ? '可计算潜在生长' : '待补齐或核对' }}
          </option>
        </select></label
      >
      <PageNavigation
        v-if="inputs"
        v-bind="inputs"
        :disabled="isLoading || isQueuing"
        @navigate="inputPage"
      />
      <label class="run-assumption-check"
        ><input v-model="acknowledged" type="checkbox" :disabled="isQueuing" />
        我已了解：这是水肥充足的潜在生长计算，参数需当地验证。</label
      >
      <button
        class="primary-button"
        :disabled="!selectedInput || !acknowledged || isQueuing || isLoading"
      >
        {{ isQueuing ? '提交中…' : '开始潜在生长计算' }}
      </button>
    </form>
    <section v-if="active" class="run-current" aria-label="当前计算任务">
      <div class="section-heading">
        <strong>{{ runLabels[active.status] }}</strong>
        <button v-if="active.result" type="button" class="text-button" @click="download">
          下载计算结果
        </button>
      </div>
      <p v-if="active.status === 'queued'" class="muted">
        任务已保存，等待计算进程处理。长时间没有变化时，请联系管理员检查计算进程。
      </p>
      <p v-if="active.status === 'running'" class="muted">正在运行模型，结果会自动更新。</p>
      <p v-if="active.status === 'failed'" class="form-error">
        {{ failureLabels[active.error_code || ''] || '计算未完成，请联系管理员核对输入与环境。' }}
      </p>
      <GrowthResultView v-if="active.result" :key="active.id" :result="active.result" />
    </section>
    <div class="input-history">
      <h3>已保存的计算记录</h3>
      <p v-if="runs?.total === 0" class="empty-guidance">
        {{ canManage ? '准备输入后开始计算，每次结果都会保留。' : '尚无计算记录，请联系管理员。' }}
      </p>
      <article v-for="run in runs?.items" :key="run.id" class="input-snapshot-row">
        <div>
          <strong>{{ runLabels[run.status] }}</strong
          ><small>{{ new Date(run.created_at).toLocaleString('zh-CN') }}</small>
        </div>
        <button type="button" class="text-button" @click="view(run.id)">查看计算记录</button>
      </article>
      <PageNavigation
        v-if="runs"
        v-bind="runs"
        :disabled="isLoading || isQueuing"
        @navigate="runPage"
      />
    </div>
  </section>
</template>
