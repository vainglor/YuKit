<script setup lang="ts">
defineProps<{
  title: string
  as?: 'section' | 'aside'
}>()
</script>

<template>
  <component :is="as ?? 'section'" class="animal-card panel">
    <header class="panel-head">
      <span>{{ title }}</span>
      <slot name="tools" />
    </header>
    <slot />
  </component>
</template>
