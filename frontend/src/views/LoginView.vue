<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { login } from '../api/modules/auth'
import { useToastStore } from '../utils/toast'

const router = useRouter()
const toast = useToastStore()

const password = ref('')
const loading = ref(false)
const showPwd = ref(false)

const IS_DEV = import.meta.env.DEV

async function handleLogin() {
  if (!password.value.trim()) {
    toast.show('请输入密码', 'error')
    return
  }
  loading.value = true
  try {
    const res = await login({ password: password.value })
    sessionStorage.setItem('neo_token', res.token)
    await router.push({ name: 'home' })
  } catch (e: any) {
    // 开发模式：后端未启动时，任意密码可直接进入预览
    if (IS_DEV && (e?.code === 'ERR_NETWORK' || e?.message?.includes('Network'))) {
      toast.show('[DEV] 后端未启动，已进入预览模式', 'info')
      sessionStorage.setItem('neo_token', 'dev-mock-token')
      await router.push({ name: 'home' })
    }
    // 生产模式下错误已由 api/base.ts 拦截器统一处理，无需再次提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-blob bg-blob--1" />
    <div class="bg-blob bg-blob--2" />

    <div class="login-card">
      <!-- Logo / 品牌区 -->
      <div class="login-brand">
        <div class="brand-icon">
          <Icon icon="material-symbols:robot-2-outline-rounded" width="36" height="36" />
        </div>
        <h1 class="brand-title">Neo-MoFox</h1>
        <p class="brand-sub">WebUI 管理面板</p>
      </div>

      <!-- 表单区 -->
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="field-wrap">
          <label class="field-label" for="pwd">管理员密码</label>
          <div class="field-input-wrap" :class="{ focused: showPwd }">
            <Icon
              class="field-icon"
              icon="material-symbols:lock-outline-rounded"
              width="20"
              height="20"
            />
            <input
              id="pwd"
              v-model="password"
              class="field-input"
              :type="showPwd ? 'text' : 'password'"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
            <button
              type="button"
              class="field-toggle"
              @click="showPwd = !showPwd"
              :aria-label="showPwd ? '隐藏密码' : '显示密码'"
            >
              <Icon
                :icon="showPwd ? 'material-symbols:visibility-off-outline-rounded' : 'material-symbols:visibility-outline-rounded'"
                width="20"
                height="20"
              />
            </button>
          </div>
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span v-if="!loading">登录</span>
          <Icon v-else icon="material-symbols:progress-activity" class="spin" width="20" height="20" />
        </button>
      </form>

      <p class="login-footer">Neo-MoFox WebUI · 管理测试界面仅供内部使用</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--md-sys-color-surface);
  position: relative;
  overflow: hidden;
}

/* 背景装饰色块 */
.bg-blob {
  position: absolute;
  border-radius: 9999px;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
}
.bg-blob--1 {
  width: 480px;
  height: 480px;
  background: var(--md-sys-color-primary);
  top: -140px;
  right: -100px;
}
.bg-blob--2 {
  width: 320px;
  height: 320px;
  background: var(--md-sys-color-secondary);
  bottom: -80px;
  left: -60px;
}

/* 卡片 */
.login-card {
  position: relative;
  z-index: 1;
  background: var(--md-sys-color-surface-container-low);
  border-radius: 2rem;
  padding: 2.5rem 2rem;
  width: min(24rem, 90vw);
  box-shadow: 0px 20px 40px rgba(24, 28, 32, 0.08);
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* 品牌区 */
.login-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
.brand-icon {
  width: 64px;
  height: 64px;
  border-radius: 1.25rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-title {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.brand-sub {
  margin: 0;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}

/* 表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.field-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.field-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  padding-left: 0.25rem;
}
.field-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 0.875rem;
  padding: 0 1rem;
  height: 3.25rem;
  transition: background 0.2s, box-shadow 0.2s;
}
.field-input-wrap:focus-within {
  background: var(--md-sys-color-surface-container-high);
  box-shadow: 0 0 0 2px var(--md-sys-color-primary);
}
.field-icon {
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}
.field-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 1rem;
  color: var(--md-sys-color-on-surface);
  outline: none;
  font-family: 'Inter', system-ui, sans-serif;
}
.field-input::placeholder {
  color: var(--md-sys-color-outline);
}
.field-toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  display: flex;
  align-items: center;
  padding: 0;
  transition: color 0.15s;
}
.field-toggle:hover {
  color: var(--md-sys-color-on-surface);
}

/* 主按钮 */
.btn-primary {
  height: 3.25rem;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(135deg, var(--md-sys-color-primary) 0%, #2771df 100%);
  color: var(--md-sys-color-on-primary);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: opacity 0.15s, transform 0.1s;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
.btn-primary:hover:not(:disabled) {
  opacity: 0.92;
}
.btn-primary:active:not(:disabled) {
  transform: scale(0.98);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 旋转动画 */
.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  margin: 0;
  text-align: center;
  font-size: 0.75rem;
  color: var(--md-sys-color-outline);
}
</style>
