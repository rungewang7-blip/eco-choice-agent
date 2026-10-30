// F2 - Calculation Engine data types

// 1. Categories supported by the F1 API
export type Category =
  | 'food'
  | 'transport'
  | 'home'
  | 'items'

// 2. Units supported by the current F1 factors
export type FactorUnit =
  | 'kg'
  | 'km'
  | 'passenger.km'
  | 'kWh'

// 3. One emission factor returned by F1
export interface Factor {
  id: string
  category: Category
  activity: string
  unit: FactorUnit
  kgCO2ePerUnit: number
  source: string
  sourceYear: number
  sourceUrl: string
  factorVersion: string
}

// 4. Full response from GET /factors
export interface FactorsResponse {
  factorVersion: string
  factors: Factor[]
}

// 5. One activity entered by the user
export interface ScenarioItem {
  factorId: string
  quantity: number
  unit: FactorUnit
}

// 6. One calculated activity result
export interface CalculationItem {
  factorId: string
  category: Category
  quantity: number
  unit: FactorUnit
  kgCO2e: number
}

// 7. Complete calculation result
export interface CalculationResult {
  factorVersion: string
  items: CalculationItem[]
  categoryTotals: Record<Category, number>
  totalKgCO2e: number
}
