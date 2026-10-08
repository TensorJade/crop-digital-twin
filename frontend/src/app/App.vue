<script setup lang="ts">
import { ref, watch } from 'vue'
import FarmPage from '../pages/FarmPage.vue'
import LoginPage from '../features/identity/LoginPage.vue'
import MembersPage from '../features/identity/MembersPage.vue'
import PasswordPanel from '../features/identity/PasswordPanel.vue'
import { useIdentity } from '../features/identity/useIdentity'
import { roleLabels } from '../features/identity/types'

const {
  identity,
  isChecking,
  isLoggingOut,
  error,
  notice,
  acceptIdentity,
  clearIdentity,
  checkIdentity,
  signOut,
} = useIdentity()
const activeView = ref<'farm' | 'members'>('farm')
const isChangingPassword = ref(false)
watch(
  () => identity.value?.user.id,
  () => {
    activeView.value = 'farm'
    isChangingPassword.value = false
  },
)
</script>

<template>
  <div v-if="isChecking" class="session-loading" role="status">正在确认登录…</div>
  <template v-else>
    <div v-if="error" class="session-error workspace-error" role="alert">
      <span>{{ error }}</span>
      <button v-if="!identity" type="button" class="text-button" @click="checkIdentity">
        重新读取
      </button>
    </div>
    <template v-if="identity">
      <header class="identity-bar">
        <div class="identity-team">
          <strong>{{ identity.organization.name }}</strong>
          <span>{{ identity.user.display_name }} · {{ roleLabels[identity.user.role] }}</span>
        </div>
        <div class="identity-actions">
          <button
            type="button"
            class="text-button"
            @click="isChangingPassword = !isChangingPassword"
          >
            修改密码
          </button>
          <button type="button" class="secondary-button" :disabled="isLoggingOut" @click="signOut">
            {{ isLoggingOut ? '退出中…' : '退出登录' }}
          </button>
        </div>
      </header>
      <nav v-if="identity.user.role === 'owner'" class="workspace-tabs" aria-label="工作区">
        <button type="button" :aria-pressed="activeView === 'farm'" @click="activeView = 'farm'">
          农田记录
        </button>
        <button
          type="button"
          :aria-pressed="activeView === 'members'"
          @click="activeView = 'members'"
        >
          成员与操作记录
        </button>
      </nav>
      <PasswordPanel
        v-if="isChangingPassword"
        @cancel="isChangingPassword = false"
        @changed="clearIdentity"
      />
      <FarmPage v-if="activeView === 'farm'" :identity="identity" />
      <MembersPage v-else :identity="identity" />
    </template>
    <LoginPage v-else :notice="notice" @authenticated="acceptIdentity" />
  </template>
</template>
