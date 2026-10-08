<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageNavigation from '../../components/PageNavigation.vue'
import type { Page } from '../../api/types'
import { createUser, listAudits, listUsers, setUserActive } from './api'
import { actionLabels, roleLabels } from './types'
import type { AuditEvent, Identity, User } from './types'

defineProps<{ identity: Identity }>()
const users = ref<Page<User> | null>(null)
const audits = ref<Page<AuditEvent> | null>(null)
const isLoadingUsers = ref(false)
const isLoadingAudits = ref(false)
const isSaving = ref(false)
const isAdding = ref(false)
const error = ref('')
const notice = ref('')
const username = ref('')
const displayName = ref('')
const password = ref('')
const role = ref<'operator' | 'viewer'>('operator')
const pendingDisableId = ref<string | null>(null)
let userGeneration = 0
let auditGeneration = 0

async function loadUsers(offset = 0) {
  const generation = ++userGeneration
  isLoadingUsers.value = true
  try {
    const result = await listUsers(offset)
    if (generation === userGeneration) users.value = result
  } catch (failure) {
    if (generation === userGeneration)
      error.value = failure instanceof Error ? failure.message : '成员读取失败'
  } finally {
    if (generation === userGeneration) isLoadingUsers.value = false
  }
}
async function loadAudits(offset = 0) {
  const generation = ++auditGeneration
  isLoadingAudits.value = true
  try {
    const result = await listAudits(offset)
    if (generation === auditGeneration) audits.value = result
  } catch (failure) {
    if (generation === auditGeneration)
      error.value = failure instanceof Error ? failure.message : '操作记录读取失败'
  } finally {
    if (generation === auditGeneration) isLoadingAudits.value = false
  }
}
async function reload() {
  error.value = ''
  await Promise.all([loadUsers(users.value?.offset ?? 0), loadAudits(audits.value?.offset ?? 0)])
}
async function saveUser() {
  if (isSaving.value) return
  isSaving.value = true
  error.value = ''
  notice.value = ''
  try {
    await createUser({
      username: username.value,
      display_name: displayName.value,
      role: role.value,
      password: password.value,
    })
    password.value = ''
    username.value = ''
    displayName.value = ''
    isAdding.value = false
    notice.value = '成员账号已建立，请通过安全方式告知对方账号与初始密码'
    await Promise.all([loadUsers(), loadAudits()])
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : '成员建立失败'
  } finally {
    isSaving.value = false
  }
}
async function changeActive(user: User) {
  if (isSaving.value) return
  isSaving.value = true
  error.value = ''
  notice.value = ''
  try {
    await setUserActive(user.id, !user.is_active)
    pendingDisableId.value = null
    notice.value = user.is_active ? '成员已停用，原有登录已失效' : '成员已启用，需要重新登录'
    await reload()
  } catch (failure) {
    error.value = failure instanceof Error ? failure.message : '成员状态修改失败'
  } finally {
    isSaving.value = false
  }
}
function toggleMemberForm() {
  isAdding.value = !isAdding.value
  if (!isAdding.value) password.value = ''
}
onMounted(() => void reload())
</script>

<template>
  <main class="farm-workspace members-workspace">
    <header class="workspace-header">
      <div>
        <p class="brand-label">{{ identity.organization.name }}</p>
        <h1>成员与操作记录</h1>
        <p class="workspace-intro">让本组织的成员各用自己的账号。</p>
      </div>
    </header>
    <div v-if="error" class="workspace-error" role="alert">
      <span>{{ error }}</span>
      <button type="button" class="text-button" @click="reload">重新读取</button>
    </div>
    <p v-if="notice" class="success-message" role="status">{{ notice }}</p>
    <section class="surface member-section" aria-labelledby="members-title">
      <div class="section-heading">
        <h2 id="members-title">组织成员</h2>
        <button type="button" class="primary-button" :disabled="isSaving" @click="toggleMemberForm">
          {{ isAdding ? '收起' : '建立成员账号' }}
        </button>
      </div>
      <p class="field-help">
        农田管理人员可记录本组织农事；只读人员只能查看。管理员负责成员与操作记录。
      </p>
      <form v-if="isAdding" class="entry-form" @submit.prevent="saveUser">
        <h3>建立成员账号</h3>
        <div class="field-pair">
          <label
            >成员账号<input
              v-model="username"
              required
              minlength="3"
              maxlength="64"
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              placeholder="3–64 位字母或数字"
          /></label>
          <label
            >成员称呼<input
              v-model="displayName"
              required
              maxlength="80"
              placeholder="例如：李师傅"
          /></label>
        </div>
        <div class="field-pair">
          <label
            >成员权限<select v-model="role" required>
              <option value="operator">农田管理</option>
              <option value="viewer">仅查看</option>
            </select></label
          >
          <label
            >初始密码<input
              v-model="password"
              type="password"
              required
              minlength="12"
              maxlength="128"
              autocomplete="new-password"
          /></label>
        </div>
        <p class="field-help">
          密码至少 12 个字符。请通过安全方式交给成员，建议其首次登录后修改密码。
        </p>
        <button class="primary-button" :disabled="isSaving">
          {{ isSaving ? '保存中…' : '保存成员' }}
        </button>
      </form>
      <p v-if="isLoadingUsers" class="muted" role="status">正在读取成员…</p>
      <ul v-else-if="users" class="member-list">
        <li v-for="user in users.items" :key="user.id" class="member-entry">
          <div>
            <strong>{{ user.display_name }}</strong
            ><span class="member-username">{{ user.username }}</span>
            <small>{{ roleLabels[user.role] }} · {{ user.is_active ? '已启用' : '已停用' }}</small>
          </div>
          <template v-if="user.role !== 'owner'">
            <div v-if="pendingDisableId === user.id" class="member-confirm">
              <p class="field-help">停用后，对方当前登录也会失效。</p>
              <button
                type="button"
                class="secondary-button"
                :disabled="isSaving"
                @click="changeActive(user)"
              >
                确认停用
              </button>
              <button
                type="button"
                class="text-button"
                :disabled="isSaving"
                @click="pendingDisableId = null"
              >
                取消
              </button>
            </div>
            <button
              v-else-if="user.is_active"
              type="button"
              class="text-button"
              :disabled="isSaving"
              :aria-label="`停用 ${user.display_name}`"
              @click="pendingDisableId = user.id"
            >
              停用
            </button>
            <button
              v-else
              type="button"
              class="text-button"
              :disabled="isSaving"
              :aria-label="`启用 ${user.display_name}`"
              @click="changeActive(user)"
            >
              启用
            </button>
          </template>
        </li>
      </ul>
      <PageNavigation
        v-if="users"
        :total="users.total"
        :limit="users.limit"
        :offset="users.offset"
        :disabled="isLoadingUsers"
        @navigate="loadUsers"
      />
    </section>
    <section class="surface audit-section" aria-labelledby="audit-title">
      <div class="section-heading">
        <h2 id="audit-title">操作记录</h2>
        <button type="button" class="text-button" :disabled="isLoadingAudits" @click="loadAudits()">
          刷新操作记录
        </button>
      </div>
      <p class="field-help">保留成功的账号与农田操作，记录操作者和时间。</p>
      <p v-if="isLoadingAudits" class="muted" role="status">正在读取操作记录…</p>
      <ol v-else-if="audits" class="audit-list">
        <li v-for="event in audits.items" :key="event.id" class="audit-entry">
          <time :datetime="event.created_at">{{
            new Date(event.created_at).toLocaleString('zh-CN', { hour12: false })
          }}</time>
          <strong>{{ actionLabels[event.action] || '系统操作' }}</strong
          ><span>{{ event.actor_display_name || '成员' }}</span>
        </li>
      </ol>
      <PageNavigation
        v-if="audits"
        :total="audits.total"
        :limit="audits.limit"
        :offset="audits.offset"
        :disabled="isLoadingAudits"
        @navigate="loadAudits"
      />
    </section>
  </main>
</template>
