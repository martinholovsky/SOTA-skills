<script setup lang="ts">
defineProps<{ posts: Post[] }>()
</script>
<template><ul><li v-for="p in posts" :key="p.id">{{ p.title }}</li></ul></template>
