<script setup lang="ts">
const { data: user } = await useFetch('/api/me')
</script>

<template><NuxtLink :to="sanitizeUrl(user.website)">Website</NuxtLink></template>
