<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

export type AnimalSelectOption = {
  value: string | number
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number
    options: AnimalSelectOption[]
    label: string
    disabled?: boolean
  }>(),
  {
    disabled: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const selectedLabel = computed(
  () => props.options.find((option) => option.value === props.modelValue)?.label ?? String(props.modelValue)
)

function toggle() {
  if (!props.disabled) {
    open.value = !open.value
  }
}

function select(value: string | number) {
  emit('update:modelValue', value)
  emit('change', value)
  open.value = false
}

function handleWindowClick(event: MouseEvent) {
  const target = event.target instanceof Node ? event.target : null
  if (target && root.value?.contains(target)) return
  open.value = false
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    open.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', handleWindowClick)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('click', handleWindowClick)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div ref="root" class="animal-select custom-select">
    <button
      class="custom-select-trigger"
      :class="{ open }"
      type="button"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-label="`${label} ${selectedLabel}`"
      :disabled="disabled"
      @click.stop="toggle"
    >
      <span>{{ selectedLabel }}</span>
      <span class="custom-select-arrow" aria-hidden="true"></span>
    </button>
    <div v-if="open" class="custom-select-menu" role="listbox">
      <button
        v-for="option in options"
        :key="option.value"
        class="custom-select-option"
        :class="{ active: option.value === modelValue }"
        type="button"
        role="option"
        :aria-selected="option.value === modelValue"
        @click.stop="select(option.value)"
      >
        <span class="custom-select-option-dot" aria-hidden="true"></span>
        <span>{{ option.label }}</span>
      </button>
    </div>
  </div>
</template>
