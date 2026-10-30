import type { FactorsResponse } from '../engine/types'

export async function getFactors(): Promise<FactorsResponse> {

  const response = await fetch('/factors')

  if (!response.ok) {
    throw new Error('Failed to load factors')
  }

  const data: FactorsResponse = await response.json()

  return data
}