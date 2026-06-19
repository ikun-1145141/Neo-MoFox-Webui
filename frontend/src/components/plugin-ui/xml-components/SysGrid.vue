<script setup lang="ts">
/**
 * SysGrid - 网格布局容器。
 *
 * CSS Grid 布局，支持 columns、gap、rows 等属性。
 */
defineProps<{
    /** 列数或 grid-template-columns 值 */
    columns?: string
    /** 行模板 */
    rows?: string
    /** 间距 */
    gap?: string
    /** 内边距 */
    padding?: string
}>()
</script>

<template>
    <div class="sys-grid" :style="{
        gridTemplateColumns: columns && /^\d+$/.test(columns) ? `repeat(${columns}, 1fr)` : columns || 'repeat(auto-fit, minmax(200px, 1fr))',
        gridTemplateRows: rows || undefined,
        gap: gap || '1rem',
        padding: padding || undefined,
    }">
        <slot />
    </div>
</template>

<style scoped>
.sys-grid {
    display: grid;
    width: 100%;
}
</style>
