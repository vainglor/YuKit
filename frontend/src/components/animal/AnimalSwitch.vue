<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: boolean
    label: string
    hint?: string
    compact?: boolean
    disabled?: boolean
  }>(),
  {
    hint: '',
    compact: false,
    disabled: false
  }
)

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <label class="animal-switch switch-row" :class="{ compact }">
    <span>
      <strong>{{ label }}</strong>
      <small v-if="hint">{{ hint }}</small>
    </span>
    <span class="animal-switch-control">
      <input
        class="animal-switch-input"
        type="checkbox"
        :checked="modelValue"
        :disabled="disabled"
        :aria-label="label"
        @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
      />
      <span class="animal-switch-track" aria-hidden="true">
        <span class="animal-switch-handle"></span>
      </span>
    </span>
  </label>
</template>
