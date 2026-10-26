<script setup lang="ts">
const posts = await $fetch('/api/posts')
</script>

<template><PostList :posts="posts" /></template>
