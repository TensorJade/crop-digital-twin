<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PageNavigation from '../../components/PageNavigation.vue'
import { correctEvent, createEvent, listEvents } from './api'
import { displayQuantity, eventLabels, localDate, unitLabels } from './types'
import type { EventInput, EventType, InputUnit, ManagementEvent, Page, Season } from './types'

const props = defineProps<{ season: Season }>()
const events = ref<Page<ManagementEvent> | null>(null)
const includeHistory = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const isAdding = ref(false)
const error = ref('')
const successMessage = ref('')
const editingId = ref<string | null>(null)
const eventType = ref<EventType>('irrigation')
const occurredOn = ref(localDate())
const quantity = ref('')
const unit = ref<InputUnit>('mm')
const materialName = ref('')
const notes = ref('')
const correctionReason = ref('')
let loadGeneration = 0
const needsQuantity = computed(
  () => eventType.value === 'irrigation' || eventType.value === 'fertilization',
)
const validUnits = computed<InputUnit[]>(() =>
  eventType.value === 'fertilization' ? ['kg/mu', 'kg/ha'] : ['mm', 'm3'],
)

function resetForm() {
  editingId.value = null
  quantity.value = ''
  materialName.value = ''
  notes.value = ''
  correctionReason.value = ''
  occurredOn.value = props.season.end_date || localDate()
  successMessage.value = ''
  error.value = ''
}

function toggleForm() {
  if (isSaving.value) return
  resetForm()
  isAdding.value = !isAdding.value
}

async function loadEvents(offset = 0) {
  const seasonId = props.season.id
  const generation = ++loadGeneration
  isLoading.value = true
  try {
    const result = await listEvents(seasonId, offset, includeHistory.value)
    if (generation === loadGeneration && seasonId === props.season.id) {
      events.value = result
      error.value = ''
    }
  } catch (failure) {
    if (generation === loadGeneration)
      error.value = failure instanceof Error ? failure.message : '农事读取失败'
  } finally {
    if (generation === loadGeneration) isLoading.value = false
  }
}

watch(
  () => props.season.id,
  () => {
    events.value = null
    includeHistory.value = false
    isAdding.value = false
    resetForm()
    void loadEvents()
  },
  { immediate: true },
)
watch(eventType, () => {
  if (!validUnits.value.includes(unit.value)) unit.value = validUnits.value[0]!
})

function editEvent(event: ManagementEvent) {
  resetForm()
  editingId.value = event.id
  isAdding.value = true
  eventType.value = event.event_type
  occurredOn.value = event.occurred_on
  quantity.value = event.quantity || ''
  unit.value = event.unit || 'mm'
  materialName.value = event.material_name || ''
  notes.value = event.notes
}

async function saveEvent() {
  if (isSaving.value) return
  const seasonId = props.season.id
  const correctionId = editingId.value
  isSaving.value = true
  error.value = ''
  successMessage.value = ''
  const input: EventInput = {
    event_type: eventType.value,
    occurred_on: occurredOn.value,
    quantity: needsQuantity.value ? Number(quantity.value) : null,
    unit: needsQuantity.value ? unit.value : null,
    material_name: eventType.value === 'fertilization' ? materialName.value : null,
    notes: notes.value,
  }
  try {
    if (correctionId) await correctEvent(correctionId, input, correctionReason.value)
    else await createEvent(seasonId, input)
    if (seasonId !== props.season.id) return
    const wasCorrection = correctionId !== null
    resetForm()
    isAdding.value = false
    successMessage.value = wasCorrection ? '农事已修正，原始记录已保留' : '农事已保存'
    await loadEvents()
  } catch (failure) {
    if (seasonId === props.season.id)
      error.value = failure instanceof Error ? failure.message : '农事保存失败'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="management-panel surface" aria-labelledby="management-title">
    <div class="section-heading">
      <div>
        <p class="step-label">第三步 · 本季管理</p>
        <h2 id="management-title">农事记录</h2>
      </div>
      <button type="button" class="primary-button" @click="toggleForm">
        {{ isAdding ? '收起表单' : '登记农事' }}
      </button>
    </div>
    <p class="muted">把每次灌溉、施肥和巡田留在这一季的记录里。</p>
    <form v-if="isAdding" class="entry-form operation-form" @submit.prevent="saveEvent">
      <h3>{{ editingId ? '修正农事' : '登记农事' }}</h3>
      <div class="field-pair">
        <label
          >农事类型<select v-model="eventType" required>
            <option v-for="(label, value) in eventLabels" :key="value" :value="value">
              {{ label }}
            </option>
          </select></label
        >
        <label
          >农事日期<input
            v-model="occurredOn"
            type="date"
            required
            :min="season.start_date"
            :max="season.end_date || undefined"
        /></label>
      </div>
      <label v-if="eventType === 'fertilization'"
        >肥料名称<input
          v-model="materialName"
          required
          maxlength="100"
          placeholder="例如：尿素、复合肥"
      /></label>
      <div v-if="needsQuantity" class="field-pair">
        <label
          >数量<input
            v-model="quantity"
            type="number"
            required
            min="0.000001"
            max="1000000"
            step="0.000001"
            inputmode="decimal"
        /></label>
        <label
          >单位<select v-model="unit" required>
            <option v-for="choice in validUnits" :key="choice" :value="choice">
              {{ unitLabels[choice] }}
            </option>
          </select></label
        >
      </div>
      <p v-if="eventType === 'fertilization'" class="field-help">
        填写实际施用的肥料产品质量，不填写推算的纯氮量。
      </p>
      <label
        >备注（选填）<textarea
          v-model="notes"
          maxlength="2000"
          rows="2"
          placeholder="记录当时的情况"
        />
      </label>
      <label v-if="editingId"
        >修正原因<input
          v-model="correctionReason"
          required
          maxlength="240"
          placeholder="例如：上次数量录入错误"
      /></label>
      <button class="primary-button" :disabled="isSaving">
        {{ isSaving ? '保存中…' : editingId ? '保存修正' : '保存农事' }}
      </button>
    </form>
    <p v-if="error" class="error-message" role="alert">{{ error }}</p>
    <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>
    <div class="record-toolbar">
      <span>{{ events?.total ?? 0 }} 条{{ includeHistory ? '记录与修订' : '有效农事' }}</span>
      <label class="checkbox-label"
        ><input
          v-model="includeHistory"
          type="checkbox"
          @change="loadEvents()"
        />查看修订历史</label
      >
    </div>
    <p v-if="isLoading" class="muted" role="status">正在读取农事…</p>
    <ol v-else-if="events?.items.length" class="operation-ledger">
      <li
        v-for="event in events.items"
        :key="event.id"
        class="ledger-entry"
        :class="{ superseded: !event.is_current }"
      >
        <time :datetime="event.occurred_on">{{ event.occurred_on }}</time>
        <div class="ledger-content">
          <div class="ledger-title">
            <strong
              >{{ eventLabels[event.event_type]
              }}<span v-if="event.material_name"> · {{ event.material_name }}</span></strong
            ><span v-if="!event.is_current" class="status-label">旧记录</span
            ><span v-else-if="event.revision > 1" class="status-label"
              >第 {{ event.revision }} 版</span
            >
          </div>
          <p v-if="event.quantity && event.unit" class="record-quantity">
            {{ displayQuantity(event.quantity) }} {{ unitLabels[event.unit]
            }}<small v-if="event.unit !== event.normalized_unit && event.normalized_quantity"
              >（{{ displayQuantity(event.normalized_quantity) }}
              {{ unitLabels[event.normalized_unit!] }}）</small
            >
          </p>
          <p v-if="event.notes" class="record-notes">{{ event.notes }}</p>
          <p v-if="event.correction_reason" class="field-help">
            修正原因：{{ event.correction_reason }}
          </p>
        </div>
        <button
          v-if="event.is_current"
          type="button"
          class="text-button"
          :aria-label="`修正 ${event.occurred_on} ${eventLabels[event.event_type]}`"
          @click="editEvent(event)"
        >
          修正
        </button>
      </li>
    </ol>
    <p v-else-if="events" class="empty-guidance">
      还没有本季农事。完成管理后，点击“登记农事”保存一次记录。
    </p>
    <PageNavigation
      v-if="events"
      v-bind="events"
      :disabled="isLoading"
      @navigate="loadEvents($event)"
    />
  </section>
</template>
