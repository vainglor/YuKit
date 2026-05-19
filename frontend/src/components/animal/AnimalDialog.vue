<script setup lang="ts">
defineProps<{
  label: string
  panelClass?: string
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <div class="overlay-backdrop" @click.self="$emit('close')">
    <section class="animal-dialog" :class="panelClass" role="dialog" aria-modal="true" :aria-label="label">
      <slot />
    </section>
  </div>
</template>
