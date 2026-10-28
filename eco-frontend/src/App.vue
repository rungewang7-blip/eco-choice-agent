<script setup lang="ts">
import { onMounted } from 'vue'

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
  <h1>EcoChoice Frontend Demo</h1>
  <p>Check browser console (F12) to view backend data.</p>
</template>

