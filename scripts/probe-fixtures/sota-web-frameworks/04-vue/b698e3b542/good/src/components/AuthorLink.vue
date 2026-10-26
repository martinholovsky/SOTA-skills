<script setup lang="ts">
import { sanitizeUrl } from '@/lib/url'
defineProps<{ user: { website: string; name: string } }>()
</script>

<template><a :href="sanitizeUrl(user.website)">{{ user.name }}</a></template>
