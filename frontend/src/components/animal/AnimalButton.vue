<script setup lang="ts">
defineOptions({ inheritAttrs: false })

withDefaults(
  defineProps<{
    variant?: 'default' | 'primary' | 'dashed' | 'text' | 'link' | 'icon'
    size?: 'small' | 'middle' | 'large'
    htmlType?: 'button' | 'submit' | 'reset'
    danger?: boolean
    ghost?: boolean
    block?: boolean
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    variant: 'default',
    size: 'middle',
    htmlType: 'button',
    danger: false,
    ghost: false,
    block: false,
    loading: false,
    disabled: false
  }
)
</script>

<template>
  <button
    v-bind="$attrs"
    class="animal-button"
    :class="[
      `animal-button-${variant}`,
      `animal-button-${size}`,
      {
        'animal-button-danger': danger,
        'animal-button-ghost': ghost,
        'animal-button-block': block,
        'animal-button-loading': loading
      }
    ]"
    :type="htmlType"
    :disabled="disabled || loading"
  >
    <span v-if="$slots.icon && !loading" class="animal-button-icon">
      <slot name="icon" />
    </span>
    <slot />
  </button>
</template>
