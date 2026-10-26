<script setup lang="ts">
const key = process.env.STRIPE_SECRET
</script>
<template><button @click="pay(key)">Pay</button></template>
