<script setup lang="ts">
import { ref, computed } from 'vue'
const q = ref('')
const trimmed = computed(() => q.value.trim())
</script>

<template><input v-model="q" /><p>{{ trimmed }}</p></template>
