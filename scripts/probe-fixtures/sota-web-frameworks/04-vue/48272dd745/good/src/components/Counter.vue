<script setup lang="ts">
import { reactive, toRefs } from 'vue'
const state = reactive({ count: 0 })
const { count } = toRefs(state)
</script>

<template><p>{{ count }}</p></template>
