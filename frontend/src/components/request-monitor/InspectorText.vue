<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '../../utils/i18n'
import { TEXT_PAGE_SIZE } from '../../utils/request-monitor-json'
const props = defineProps<{ text: string }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const limit = ref(TEXT_PAGE_SIZE)
// 流式文本追加时，保留用户已经展开的范围。
watch(() => props.text, (next, old) => { if (!next.startsWith(old)) limit.value = TEXT_PAGE_SIZE })
const preview = computed(() => props.text.slice(0, limit.value))
</script>
<template>
  <div class="rm-text-view">
    <pre class="rm-content">{{ preview }}</pre>
    <div class="rm-text-actions">
      <button v-if="text.length > limit" class="rm-btn rm-btn-tonal rm-text-expand-btn" @click="limit += TEXT_PAGE_SIZE">{{ t('requestMonitor.moreText') }} ({{ Math.min(limit, text.length) }}/{{ text.length }})</button>
      <button class="rm-btn rm-btn-tonal" @click="emit('copy', text)">{{ t('requestMonitor.copyText') }}</button>
    </div>
  </div>
</template>
