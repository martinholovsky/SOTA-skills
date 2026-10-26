<script setup lang="ts">
const { data: posts } = await useFetch('/api/posts')
</script>

<template><PostList :posts="posts" /></template>
