<!--
  @file SelectField.vue
  @description 选择字段组件（下拉选择）- 使用 MD3 Select 组件
-->
<template>
  <MdSelect
    :modelValue="modelValue"
    @update:modelValue="handleUpdate"
    :options="(field.choices as Array<string | number | { label: string; value: string | number }>) || []"
    :disabled="readonly"
    :label="field.label"
  />
</template>

<script setup lang="ts">
import MdSelect from '@/components/common/MdSelect.vue'
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: string | number
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function handleUpdate(value: string | number | null) {
  if (value !== null) {
    emit('update:modelValue', value)
  }
}
</script>
