<script setup lang="ts">
import { ref } from 'vue'
import { login } from './api'
import type { Identity } from './types'

defineProps<{ notice: string }>()
const emit = defineEmits<{ authenticated: [identity: Identity] }>()
const username = ref('')
const password = ref('')
const isSaving = ref(false)
const error = ref('')
async function signIn() {
  if (isSaving.value) return
  isSaving.value = true
  error.value = ''
  try {
    const result = await login(username.value, password.value)
    password.value = ''
    emit('authenticated', result)
  } catch (failure) {
    password.value = ''
    error.value = failure instanceof Error ? failure.message : '登录失败，请重试'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <main class="login-workspace">
    <section class="login-intro">
      <p class="brand-label">华南水稻 · 农田管理</p>
      <h1>把这一季记录好</h1>
      <p>地块、种植季和每一次农事，放在同一本记录里。</p>
      <ol class="login-ledger">
        <li><strong>地块</strong><span>田在哪里，有多大</span></li>
        <li><strong>种植季</strong><span>播种或移栽从哪天开始</span></li>
        <li><strong>农事</strong><span>灌溉、施肥与巡田的实际记录</span></li>
      </ol>
    </section>
    <section class="login-surface surface">
      <p class="step-label">进入自己的组织</p>
      <h2>登录我的农田</h2>
      <p class="field-help">使用管理员提供的账号。</p>
      <p v-if="notice" class="success-message" role="status">{{ notice }}</p>
      <form class="login-form" @submit.prevent="signIn">
        <label
          >账号<input
            v-model="username"
            required
            maxlength="64"
            autocomplete="username"
            placeholder="填写账号"
            autocapitalize="none"
            spellcheck="false"
        /></label>
        <label
          >密码<input
            v-model="password"
            type="password"
            required
            maxlength="128"
            autocomplete="current-password"
            placeholder="填写密码"
        /></label>
        <p v-if="error" class="error-message" role="alert">{{ error }}</p>
        <button class="primary-button" :disabled="isSaving">
          {{ isSaving ? '登录中…' : '登录' }}
        </button>
      </form>
      <p class="field-help login-help">账号登录遇到问题时，请联系组织管理员。</p>
    </section>
  </main>
</template>
