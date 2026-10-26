<script setup lang="ts">
import { ref, watch } from 'vue'
const q = ref('')
setTimeout(() => {
  watch(q, (v) => search(v))
}, 100)
</script>

<template><input v-model="q" /></template>
