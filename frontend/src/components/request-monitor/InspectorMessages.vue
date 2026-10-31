<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import InspectorText from './InspectorText.vue'
import { useI18n } from '../../utils/i18n'
import type { InspectorMessageView } from '../../api/types/request-inspector'
const props = defineProps<{
  messages: InspectorMessageView[]
  recordKey: string
  title?: string
}>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const limit = ref(100)
const opened = reactive(new Map<number, boolean>())
function toggle(index: number, event: Event) { opened.set(index, (event.target as HTMLDetailsElement).open) }
const role = ref('')
const roles = computed(() => [
  ...new Set(props.messages.map((message) => message.role)),
])
const visible = computed(() =>
  props.messages.filter(
    (message) => !role.value || role.value === message.role,
  ),
)
watch(
  () => props.recordKey,
  () => {
    role.value = ''
    limit.value = 100
    opened.clear()
  },
)
</script>
<template>
  <div class="rm-section-heading">
    <h3>
      {{ title || t('requestMonitor.messages') }}
      <span class="rm-muted">{{ messages.length }}</span>
    </h3>
    <select
      v-model="role"
      class="rm-input rm-role-filter"
      :aria-label="t('requestMonitor.filterRole')"
    >
      <option value="">{{ t('requestMonitor.allRoles') }}</option>
      <option v-for="value in roles" :key="value" :value="value">
        {{ value }}
      </option>
    </select>
  </div>
  <p v-if="!visible.length" class="rm-empty">
    {{ t('requestMonitor.noMessages') }}
  </p>
  <details
    v-for="message in visible.slice(0, limit)"
    :key="message.index"
    class="rm-block"
    :open="opened.get(message.index) ?? message.index < 3"
    @toggle="toggle(message.index, $event)"
  >
    <summary>
      <span class="rm-role">{{ message.label }}</span
      ><span class="rm-muted rm-mono"
        >#{{ message.index }} {{ message.meta }}</span
      >
    </summary>
    <template v-if="opened.get(message.index) ?? message.index < 3">
    <div
      v-for="(block, index) in message.blocks"
      :key="index"
      class="rm-message-block"
    >
      <div class="rm-section-heading">
        <strong>{{ block.label || block.type }}</strong
        ><span v-if="block.name" class="rm-mono">{{ block.name }}</span>
      </div>
      <InspectorText :text="block.arguments_text ?? block.text ?? block.meta ?? '—'" @copy="emit('copy', $event)" />
      <p v-if="block.call_id" class="rm-muted rm-mono">
        call_id: {{ block.call_id }}
      </p>
    </div>
    </template>
  </details>
  <button v-if="visible.length > limit" class="rm-button" @click="limit += 100">{{ t('requestMonitor.moreChildren') }}</button>
</template>
