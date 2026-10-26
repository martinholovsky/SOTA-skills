<script setup lang="ts">
defineProps<{ body: string }>()
</script>

<template><div class="comment" v-html="body"></div></template>
