<script setup lang="ts">
import { ref } from 'vue'
import { getApiHealth } from '../api/client'

const isChecking = ref(false)
const connectionMessage = ref('尚未检查连接')

async function checkConnection() {
  isChecking.value = true
  try {
    const health = await getApiHealth()
    connectionMessage.value = `API 已连接 · v${health.version} · 仅验证进程存活`
  } catch (error) {
    connectionMessage.value = error instanceof Error ? error.message : '连接失败，请启动后端'
  } finally {
    isChecking.value = false
  }
}
</script>

<template>
  <main class="workspace">
    <p class="eyebrow">CROP DIGITAL TWIN / DEVELOPMENT</p>
    <h1>作物数字孪生开发工作区</h1>
    <p class="intro">前后端入口已建立。这里用于检查本地开发环境，业务功能将按需求逐项实现。</p>
    <section class="panel" aria-labelledby="connection-title">
      <h2 id="connection-title">本地服务连接</h2>
      <button :disabled="isChecking" @click="checkConnection">
        {{ isChecking ? '检查中…' : '检查后端连接' }}
      </button>
      <p role="status" aria-live="polite">{{ connectionMessage }}</p>
      <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noopener noreferrer"
        >打开 API 文档</a
      >
    </section>
    <section class="panel" aria-labelledby="scope-title">
      <h2 id="scope-title">后续开发模块</h2>
      <ul>
        <li>地块、种植季和农事管理</li>
        <li>天气与土壤数据、PCSE/WOFOST 生长模拟</li>
        <li>卫星底图、作物矢量展示与时间轴</li>
        <li>无人机影像质控、长势反演和模型校准</li>
      </ul>
      <p class="note">以上业务功能尚未实现。当前页面不展示真实农田、遥感结果或模拟产量。</p>
    </section>
  </main>
</template>
