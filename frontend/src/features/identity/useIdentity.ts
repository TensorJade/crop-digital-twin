/** Root-owned session state; farm modules receive public identity facts through props. */
import { onMounted, ref } from 'vue'
import { ApiError, setCsrfToken, setUnauthorizedHandler } from '../../api/http'
import { getIdentity, logout } from './api'
import type { Identity } from './types'

export function useIdentity() {
  const identity = ref<Identity | null>(null)
  const isChecking = ref(true)
  const isLoggingOut = ref(false)
  const error = ref('')
  const notice = ref('')
  let generation = 0

  function acceptIdentity(value: Identity) {
    ++generation
    identity.value = value
    setCsrfToken(value.csrf_token)
    error.value = ''
    notice.value = ''
    isChecking.value = false
  }

  function clearIdentity(message = '') {
    ++generation
    identity.value = null
    setCsrfToken('')
    notice.value = message
    isChecking.value = false
  }

  setUnauthorizedHandler(() => {
    if (identity.value) clearIdentity('登录已失效，请重新登录')
  })

  async function checkIdentity() {
    const requestGeneration = ++generation
    isChecking.value = true
    error.value = ''
    try {
      const result = await getIdentity()
      if (requestGeneration === generation) acceptIdentity(result)
    } catch (failure) {
      if (
        requestGeneration === generation &&
        !(failure instanceof ApiError && failure.status === 401)
      )
        error.value = failure instanceof Error ? failure.message : '登录状态读取失败'
    } finally {
      isChecking.value = false
    }
  }

  async function signOut() {
    if (isLoggingOut.value) return
    isLoggingOut.value = true
    error.value = ''
    try {
      await logout()
      clearIdentity('已退出登录')
    } catch (failure) {
      if (identity.value)
        error.value = failure instanceof Error ? failure.message : '退出失败，请重试'
    } finally {
      isLoggingOut.value = false
    }
  }
  onMounted(() => void checkIdentity())
  return {
    identity,
    isChecking,
    isLoggingOut,
    error,
    notice,
    acceptIdentity,
    clearIdentity,
    checkIdentity,
    signOut,
  }
}
