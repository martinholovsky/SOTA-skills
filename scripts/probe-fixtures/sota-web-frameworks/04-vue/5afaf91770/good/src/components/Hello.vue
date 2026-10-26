<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ name: string }>()
const greeting = ref('Hello')
</script>

<template><p>{{ greeting }} {{ name }}</p></template>
