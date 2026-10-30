<script setup lang="ts">
import { onMounted } from 'vue'
import BenchmarkAdmin from './BenchmarkAdmin.vue'

import { getFactors } from './api/factors'
import { calculateScenario } from './engine/calculate'
import { formatEmission } from './engine/format'

// Test F1 API and F2 calculation engine together
onMounted(async () => {
  try {
    // Step 1: Get real emission factors from F1
    const referenceData = await getFactors()

    console.log('Fetched carbon factor data:', referenceData)

    // Step 2: Create a sample scenario
    const scenario = [
      { factorId: 'beef', quantity: 2, unit: 'kg' }
    ] as const

    // Step 3: Calculate carbon emissions locally
    const result = calculateScenario(
      [...scenario],
      referenceData
    )

    // Step 4: Show calculation result
    console.log('F2 calculation result:', result)
    console.log('F2 formatted result:', formatEmission(result.totalKgCO2e))

  } catch (err) {
    console.error('Failed to calculate carbon emissions:', err)
  }
})
</script>

<template>
  <BenchmarkAdmin />
</template>