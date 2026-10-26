<script setup lang="ts">
defineProps<{ user: { website: string; name: string } }>()
</script>

<template><a :href="user.website">{{ user.name }}</a></template>
