<script setup lang="ts">
import { ref } from 'vue'
import { changePassword } from './api'
const emit = defineEmits<{ changed: [message: string]; cancel: [] }>()
const currentPassword = ref('')
const newPassword = ref('')
const confirmation = ref('')
const error = ref('')
const isSaving = ref(false)
async function savePassword() {
  if (isSaving.value) return
  error.value = ''
  if (newPassword.value !== confirmation.value) {
    error.value = '两次新密码不同，请重新填写'
    return
  }
  isSaving.value = true
  try {
    const result = await changePassword(currentPassword.value, newPassword.value)
    currentPassword.value = ''
    newPassword.value = ''
    confirmation.value = ''
    emit('changed', result.message)
  } catch (failure) {
    currentPassword.value = ''
    error.value = failure instanceof Error ? failure.message : '密码修改失败'
  } finally {
    isSaving.value = false
  }
}
</script>
<template>
  <section class="account-panel surface" aria-labelledby="password-title">
    <div class="section-heading">
      <h2 id="password-title">修改密码</h2>
      <button type="button" class="text-button" :disabled="isSaving" @click="emit('cancel')">
        取消
      </button>
    </div>
    <form class="login-form" @submit.prevent="savePassword">
      <label
        >当前密码<input
          v-model="currentPassword"
          type="password"
          required
          maxlength="128"
          autocomplete="current-password"
      /></label>
      <div class="field-pair">
        <label
          >新密码<input
            v-model="newPassword"
            type="password"
            required
            minlength="12"
            maxlength="128"
            autocomplete="new-password"
        /></label>
        <label
          >再次填写新密码<input
            v-model="confirmation"
            type="password"
            required
            minlength="12"
            maxlength="128"
            autocomplete="new-password"
        /></label>
      </div>
      <p class="field-help">密码需 12–128 个字符。修改后所有设备都需要重新登录。</p>
      <p v-if="error" class="error-message" role="alert">{{ error }}</p>
      <button class="primary-button" :disabled="isSaving">
        {{ isSaving ? '保存中…' : '保存新密码' }}
      </button>
    </form>
  </section>
</template>
