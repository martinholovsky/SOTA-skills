<script setup lang="ts">
const debug = process.env.NODE_ENV !== 'production'
</script>
<template><button @click="pay(debug)">Pay</button></template>
