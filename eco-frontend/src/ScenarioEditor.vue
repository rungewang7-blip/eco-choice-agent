
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getFactors } from './api/factors'
import { calculateScenario } from './engine/calculate'
import { formatEmission } from './engine/format'
import type {
  FactorsResponse,
  Factor,
  ScenarioItem,
  FactorUnit
} from './engine/types'

// F1 reference data
const referenceData = ref<FactorsResponse | null>(null)
const loading = ref(true)
const error = ref('')

// User scenario stays in the browser
const scenario = ref<ScenarioItem[]>([])

// Load public factors from F1
onMounted(async () => {
  try {
    referenceData.value = await getFactors()
  } catch {
    error.value = 'Failed to load carbon factors'
  } finally {
    loading.value = false
  }
})

// Available activities
const factors = computed<Factor[]>(
  () => referenceData.value?.factors ?? []
)

// Add a new activity
function addActivity() {
  const factor = factors.value[0]
  if (!factor) return

  scenario.value.push({
    factorId: factor.id,
    quantity: 1,
    unit: factor.unit
  })
}

// Remove an activity
function removeActivity(index: number) {
  scenario.value.splice(index, 1)
}

// Update selected factor and its unit
function updateFactor(index: number, factorId: string) {
  const factor = factors.value.find(f => f.id === factorId)
  const item = scenario.value[index]

  if (!factor || !item) return

  item.factorId = factor.id
  item.unit = factor.unit
}

// Update quantity
function updateQuantity(index: number, value: string) {
  const item = scenario.value[index]
  if (!item) return

  item.quantity = value.trim() === '' ? NaN : Number(value)
}

// Validate scenario before calculation
const validationError = computed(() => {
  for (const item of scenario.value) {
    if (!Number.isFinite(item.quantity) || item.quantity < 0) {
      return 'Quantity must be a non-negative number'
    }
  }
  return ''
})

// Calculate locally using F2
const result = computed(() => {
  if (!referenceData.value || validationError.value) return null

  try {
    return calculateScenario(scenario.value, referenceData.value)
  } catch {
    return null
  }
})

// Display categories
const categories = [
  { key: 'food', label: 'Food' },
  { key: 'transport', label: 'Transport' },
  { key: 'home', label: 'Home' },
  { key: 'items', label: 'Items' }
] as const

function unitOf(factorId: string): FactorUnit | '' {
  return factors.value.find(f => f.id === factorId)?.unit ?? ''
}
</script>

<template>
  <main class="scenario-editor">
    <h1>EcoChoice Carbon Calculator</h1>
    <p>Create one scenario and calculate its carbon footprint.</p>

    <p v-if="loading">Loading carbon factors...</p>

    <p v-else-if="error" role="alert">{{ error }}</p>

    <template v-else>
      <p>
        Factor version:
        {{ referenceData?.factorVersion }}
      </p>

      <h2>Activities</h2>

      <div
        v-for="(item, index) in scenario"
        :key="index"
        class="activity-row"
      >
        <label>
          Activity
          <select
            :value="item.factorId"
            @change="updateFactor(index, ($event.target as HTMLSelectElement).value)"
          >
            <option
              v-for="factor in factors"
              :key="factor.id"
              :value="factor.id"
            >
              {{ factor.activity }} ({{ factor.category }})
            </option>
          </select>
        </label>

        <label>
          Quantity ({{ unitOf(item.factorId) }})
          <input
            type="number"
            min="0"
            step="any"
            :value="Number.isNaN(item.quantity) ? '' : item.quantity"
            @input="updateQuantity(index, ($event.target as HTMLInputElement).value)"
          />
        </label>

        <button type="button" @click="removeActivity(index)">
          Remove
        </button>
      </div>

      <button
        type="button"
        :disabled="factors.length === 0"
        @click="addActivity"
      >
        Add activity
      </button>

      <p v-if="validationError" role="alert">
        {{ validationError }}
      </p>

      <section v-if="result && !validationError">
        <h2>Calculation Results</h2>

        <p>
          <strong>Total:</strong>
          {{ formatEmission(result.totalKgCO2e) }} kgCO₂e
        </p>

        <h3>Category Breakdown</h3>

        <ul>
          <li v-for="category in categories" :key="category.key">
            {{ category.label }}:
            {{ formatEmission(result.categoryTotals[category.key]) }}
            kgCO₂e
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>

<style scoped>
.scenario-editor {
  max-width: 850px;
  margin: 40px auto;
  padding: 24px;
  font-family: Arial, sans-serif;
}

.activity-row {
  display: flex;
  gap: 12px;
  align-items: end;
  flex-wrap: wrap;
  margin: 16px 0;
  padding: 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

input,
select,
button {
  padding: 9px;
  font-size: 14px;
}

button {
  cursor: pointer;
}

section {
  margin-top: 24px;
  padding: 20px;
  background: #f5f7f8;
  border-radius: 8px;
}
/* Remove category list bullet points */
ul {
  list-style: none;
  padding: 0;
}

li {
  margin: 8px 0;
}
</style>
