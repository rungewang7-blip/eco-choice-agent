import type {
  Category,
  FactorsResponse,
  ScenarioItem,
  CalculationItem,
  CalculationResult
} from './types'

export function calculateScenario(
  scenario: ScenarioItem[],
  referenceData: FactorsResponse
): CalculationResult {

  const items: CalculationItem[] = []

  const categoryTotals: Record<Category, number> = {
    food: 0,
    transport: 0,
    home: 0,
    items: 0
  }

  let totalKgCO2e = 0

  // Calculate each activity
  for (const activity of scenario) {

    // Check quantity
    if (!Number.isFinite(activity.quantity) || activity.quantity < 0) {
      throw new Error('Invalid quantity')
    }

    // Find emission factor from F1 data
    const factor = referenceData.factors.find(
      factor => factor.id === activity.factorId
    )

    if (!factor) {
      throw new Error('Unknown factor')
    }

    // Check unit
    if (activity.unit !== factor.unit) {
      throw new Error('Wrong unit')
    }

    // Check emission factor
    if (
      !Number.isFinite(factor.kgCO2ePerUnit) ||
      factor.kgCO2ePerUnit < 0
    ) {
      throw new Error('Invalid emission factor')
    }

    // Calculate emissions
    const emission = activity.quantity * factor.kgCO2ePerUnit

    if (!Number.isFinite(emission)) {
      throw new Error('Invalid emission')
    }

    // Save result
    items.push({
      factorId: activity.factorId,
      category: factor.category,
      quantity: activity.quantity,
      unit: activity.unit,
      kgCO2e: emission
    })

    // Add emissions to totals
    categoryTotals[factor.category] += emission
    totalKgCO2e += emission

    // Check total emissions
    if (
      !Number.isFinite(categoryTotals[factor.category]) ||
      !Number.isFinite(totalKgCO2e)
    ) {
      throw new Error('Invalid total emission')
    }
  }

  return {
    factorVersion: referenceData.factorVersion,
    items: items,
    categoryTotals: categoryTotals,
    totalKgCO2e: totalKgCO2e
  }
}