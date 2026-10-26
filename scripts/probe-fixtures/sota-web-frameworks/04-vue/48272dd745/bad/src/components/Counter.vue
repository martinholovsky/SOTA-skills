<script setup lang="ts">
import { reactive } from 'vue'
const { count } = reactive({ count: 0 })
</script>

<template><p>{{ count }}</p></template>
