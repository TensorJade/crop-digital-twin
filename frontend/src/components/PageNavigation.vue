<script setup lang="ts">
defineProps<{ total: number; limit: number; offset: number; disabled?: boolean }>()
defineEmits<{ navigate: [offset: number] }>()
</script>

<template>
  <nav v-if="total > limit" class="page-navigation" aria-label="分页">
    <button
      type="button"
      class="text-button"
      :disabled="disabled || offset === 0"
      @click="$emit('navigate', Math.max(0, offset - limit))"
    >
      上一页
    </button>
    <span>{{ Math.floor(offset / limit) + 1 }} / {{ Math.ceil(total / limit) }}</span>
    <button
      type="button"
      class="text-button"
      :disabled="disabled || offset + limit >= total"
      @click="$emit('navigate', offset + limit)"
    >
      下一页
    </button>
  </nav>
</template>
