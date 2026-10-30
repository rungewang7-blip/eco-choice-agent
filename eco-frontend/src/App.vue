
<script setup lang="ts">
import { onMounted } from 'vue'
import BenchmarkAdmin from './BenchmarkAdmin.vue'

// Keep the existing F1 carbon factor API check.
onMounted(async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/factors')
    const result = await response.json()
    console.log('Fetched carbon factor data:', result)
  } catch (err) {
    console.error('Failed to load data from backend', err)
  }
})
</script>

<template>
  <BenchmarkAdmin />
</template>
