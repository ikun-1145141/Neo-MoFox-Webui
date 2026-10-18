<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '../../utils/i18n'
import { TEXT_PAGE_SIZE } from '../../utils/request-monitor-json'
const props = defineProps<{ text: string }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const limit = ref(TEXT_PAGE_SIZE)
// Appended streaming text retains the user's expanded range.
watch(() => props.text, (next, old) => { if (!next.startsWith(old)) limit.value = TEXT_PAGE_SIZE })
const preview = computed(() => props.text.slice(0, limit.value))
</script>
<template>
  <div class="rm-text-view">
    <pre class="rm-content">{{ preview }}</pre>
    <div class="rm-inline-actions">
      <button v-if="text.length > limit" class="rm-button" @click="limit += TEXT_PAGE_SIZE">{{ t('requestMonitor.moreText') }} ({{ Math.min(limit, text.length) }}/{{ text.length }})</button>
      <button class="rm-button rm-small" @click="emit('copy', text)">{{ t('requestMonitor.copyText') }}</button>
    </div>
  </div>
</template>
