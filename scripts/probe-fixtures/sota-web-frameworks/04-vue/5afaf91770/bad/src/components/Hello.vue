<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  props: { name: String },
  data() { return { greeting: 'Hello' } },
})
</script>

<template><p>{{ greeting }} {{ name }}</p></template>
