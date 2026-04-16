<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { getSettings, saveSettings } from '../../api/modules/settings'
import { useToastStore } from '../../utils/toast'
import type { SettingsData } from '../../api/types/base'

const toast = useToastStore()
const loading = ref(true)
const saving = ref(false)

const settings = ref<SettingsData>({
  theme: 'auto',
  theme_source_color: '#0058bd',
  language: 'zh_CN',
  bot_name: 'Neo-MoFox',
  wallpaper_path: null,
})

const IS_DEV = import.meta.env.DEV

async function fetchSettings() {
  loading.value = true
  try {
    settings.value = await getSettings()
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，使用默认配置', 'info')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await saveSettings(settings.value)
    toast.show('设置已保存', 'success')
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，预览模式下更改不会持久化', 'info')
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="general-view">
    <div class="view-header">
      <h2 class="view-title">通用设置</h2>
      <p class="view-sub">机器人基础信息与语言配置</p>
    </div>

    <div v-if="loading" class="loading-wrap">
      <Icon icon="material-symbols:progress-activity" class="spin" width="32" height="32" />
    </div>

    <template v-else>
      <section class="setting-section">
        <div class="field-row">
          <label class="field-label">机器人名称</label>
          <div class="field-input-wrap">
            <Icon icon="material-symbols:robot-2-outline-rounded" width="18" height="18" class="field-icon" />
            <input v-model="settings.bot_name" type="text" class="field-input" placeholder="Neo-MoFox" />
          </div>
        </div>

        <div class="field-row">
          <label class="field-label">语言</label>
          <div class="field-input-wrap">
            <Icon icon="material-symbols:language-rounded" width="18" height="18" class="field-icon" />
            <select v-model="settings.language" class="field-input">
              <option value="zh_CN">简体中文</option>
              <option value="en_US">English</option>
            </select>
          </div>
        </div>
      </section>

      <div class="actions-row">
        <button class="btn-outlined" @click="fetchSettings" :disabled="saving">
          <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
          重新获取
        </button>
        <button class="btn-primary" @click="handleSave" :disabled="saving">
          <Icon v-if="saving" icon="material-symbols:progress-activity" class="spin" width="18" height="18" />
          <Icon v-else icon="material-symbols:save-outline-rounded" width="18" height="18" />
          {{ saving ? '保存中…' : '保存设置' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.general-view { display: flex; flex-direction: column; gap: 2rem; }
.view-title {
  margin: 0 0 0.375rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.view-sub { margin: 0; font-size: 0.875rem; color: var(--md-sys-color-on-surface-variant); }
.loading-wrap {
  display: flex; justify-content: center; padding: 3rem;
  color: var(--md-sys-color-on-surface-variant);
}
.setting-section {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1.25rem; padding: 1.5rem;
  display: flex; flex-direction: column; gap: 1.25rem;
}
.field-row { display: flex; flex-direction: column; gap: 0.5rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: var(--md-sys-color-on-surface-variant); padding-left: 0.25rem; }
.field-input-wrap {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 0.875rem; padding: 0 1rem; height: 3rem;
  transition: background 0.2s, box-shadow 0.2s;
}
.field-input-wrap:focus-within {
  background: var(--md-sys-color-surface-container-high);
  box-shadow: 0 0 0 2px var(--md-sys-color-primary);
}
.field-icon { color: var(--md-sys-color-on-surface-variant); flex-shrink: 0; }
.field-input {
  flex: 1; border: none; background: transparent;
  font-size: 1rem; color: var(--md-sys-color-on-surface); outline: none;
  font-family: 'Inter', system-ui, sans-serif;
}
.field-input::placeholder { color: var(--md-sys-color-outline); }
.actions-row { display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-primary {
  display: flex; align-items: center; gap: 0.5rem;
  height: 2.75rem; padding: 0 1.5rem; border: none; border-radius: 9999px;
  background: linear-gradient(135deg, var(--md-sys-color-primary) 0%, #2771df 100%);
  color: var(--md-sys-color-on-primary);
  font-size: 0.9375rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outlined {
  display: flex; align-items: center; gap: 0.5rem;
  height: 2.75rem; padding: 0 1.25rem; border: none; border-radius: 9999px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-outlined:hover { background: var(--md-sys-color-surface-container-highest); }
.btn-outlined:disabled { opacity: 0.5; cursor: not-allowed; }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
