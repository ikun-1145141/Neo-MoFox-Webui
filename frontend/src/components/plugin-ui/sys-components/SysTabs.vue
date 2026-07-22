<script setup lang="ts">
/**
 * SysTabs - 标签页容器。
 *
 * 子节点作为各 tab 的内容，每个子节点可通过 `label` 属性指定 tab 标题。
 * 不依赖 slot name，通过遍历 default slot 的 vnode 实现。
 */
import { ref, computed, useSlots, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 默认激活的 tab 索引（从 0 开始） */
    defaultTab?: string
    /** 标签位置：top / bottom / start / end */
    placement?: string
    /** 是否填满内容区高度 */
    fill?: boolean
  }>(),
  {
    defaultTab: '0',
    placement: 'top',
    fill: false,
  }
)

const emit = defineEmits<{
  (e: 'change', index: number, label: string): void
}>()

const slots = useSlots()
const activeIndex = ref(parseInt(props.defaultTab) || 0)

/** 默认插槽中过滤出的有效 vnode（带 props 的元素） */
const tabVnodes = computed(() => {
  const raw = slots.default?.() || []
  return raw.filter((v) => v && v.props != null && (v.props.label || v.props['data-label']))
})

const tabLabels = computed(() =>
  tabVnodes.value.map((v, i) => (v.props?.label || v.props?.['data-label'] || `Tab ${i + 1}`) as string)
)

// 切换时校验边界
watch(
  [() => props.defaultTab, tabVnodes],
  ([defaultIdx, vnodes]) => {
    const parsed = parseInt(String(defaultIdx)) || 0
    if (vnodes.length && parsed >= vnodes.length) {
      activeIndex.value = 0
    } else if (parsed !== activeIndex.value && parsed >= 0 && parsed < vnodes.length) {
      activeIndex.value = parsed
    }
  }
)

function selectTab(i: number): void {
  if (i === activeIndex.value) return
  activeIndex.value = i
  emit('change', i, tabLabels.value[i] || '')
}
</script>

<template>
  <div
    class="sys-tabs"
    :class="[`sys-tabs--${placement}`, { 'sys-tabs--fill': fill }]"
  >
    <div class="sys-tabs-header" role="tablist">
      <button
        v-for="(label, i) in tabLabels"
        :key="i"
        class="sys-tabs-tab"
        :class="{ 'sys-tabs-tab--active': activeIndex === i }"
        role="tab"
        :aria-selected="activeIndex === i"
        @click="selectTab(i)"
      >
        <span class="sys-tabs-tab-label">{{ label }}</span>
        <span class="sys-tabs-tab-indicator" />
      </button>
    </div>
    <div class="sys-tabs-content">
      <Transition name="sys-fade" mode="out-in">
        <component
          :is="tabVnodes[activeIndex]"
          v-if="tabVnodes[activeIndex]"
          :key="activeIndex"
        />
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.sys-tabs {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
}

.sys-tabs--bottom {
  flex-direction: column-reverse;
}

.sys-tabs--start {
  flex-direction: row;
}

.sys-tabs--end {
  flex-direction: row-reverse;
}

.sys-tabs-header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  overflow-x: auto;
  flex-shrink: 0;
}

.sys-tabs--bottom .sys-tabs-header {
  border-bottom: none;
  border-top: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}

.sys-tabs--start .sys-tabs-header,
.sys-tabs--end .sys-tabs-header {
  flex-direction: column;
  border-bottom: none;
  border-right: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  width: 200px;
}

.sys-tabs--end .sys-tabs-header {
  border-right: none;
  border-left: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}

.sys-tabs-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0.625rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  transition:
    color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-tabs-tab:hover {
  color: var(--md-sys-color-primary, #0058bd);
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 4%, transparent);
}

.sys-tabs-tab--active {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-tabs-tab-label {
  display: inline-block;
}

.sys-tabs-tab-indicator {
  position: absolute;
  left: 50%;
  bottom: -1px;
  width: 100%;
  height: 2px;
  background: var(--md-sys-color-primary, #0058bd);
  border-radius: 2px 2px 0 0;
  transform: translateX(-50%) scaleX(0);
  opacity: 0;
  transition:
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized),
    opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-tabs-tab--active .sys-tabs-tab-indicator {
  transform: translateX(-50%) scaleX(1);
  opacity: 1;
}

.sys-tabs--start .sys-tabs-tab-indicator,
.sys-tabs--end .sys-tabs-tab-indicator {
  left: auto;
  right: -1px;
  bottom: 0;
  top: 0;
  width: 2px;
  height: 100%;
  border-radius: 2px 0 0 2px;
  transform: translateY(0) scaleY(0);
  transform-origin: center;
}

.sys-tabs--start .sys-tabs-tab--active .sys-tabs-tab-indicator,
.sys-tabs--end .sys-tabs-tab--active .sys-tabs-tab-indicator {
  transform: translateY(0) scaleY(1);
}

.sys-tabs-content {
  flex: 1;
  padding-top: 1rem;
  min-height: 0;
  min-width: 0;
}

.sys-tabs--fill .sys-tabs-content {
  display: flex;
}

.sys-tabs--fill .sys-tabs-content > * {
  flex: 1;
}
</style>
