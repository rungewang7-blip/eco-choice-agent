import { describe, it, expect } from 'vitest'
import { calculateScenario } from '../src/engine/calculate'
import type { FactorsResponse } from '../src/engine/types'

// Sample data from F1, only used for testing
const referenceData: FactorsResponse = {
  factorVersion: '2026-10-f1',
  factors: [
    {
      id: 'beef',
      category: 'food',
      activity: 'Beef',
      unit: 'kg',
      kgCO2ePerUnit: 99.48,
      source: 'Poore and Nemecek 2018',
      sourceYear: 2018,
      sourceUrl: 'https://ourworldindata.org',
      factorVersion: '2026-10-f1'
    },
    {
      id: 'bus',
      category: 'transport',
      activity: 'Bus',
      unit: 'passenger.km',
      kgCO2ePerUnit: 0.10385,
      source: 'DESNZ 2025',
      sourceYear: 2025,
      sourceUrl: 'https://www.gov.uk',
      factorVersion: '2026-10-f1'
    }
  ]
}

describe('F2 Calculation Engine', () => {

  // Test 1: Calculate one activity
  it('calculates one activity', () => {
    const result = calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      referenceData
    )

    expect(result.totalKgCO2e).toBeCloseTo(198.96)
  })

  // Test 2: Calculate category totals
  it('calculates category totals', () => {
    const result = calculateScenario(
      [
        { factorId: 'beef', quantity: 2, unit: 'kg' },
        { factorId: 'bus', quantity: 10, unit: 'passenger.km' }
      ],
      referenceData
    )

    expect(result.categoryTotals.food).toBeCloseTo(198.96)
    expect(result.categoryTotals.transport).toBeCloseTo(1.0385)
    expect(result.totalKgCO2e).toBeCloseTo(199.9985)
  })

  // Test 3: Empty scenario
  it('returns zero for empty scenario', () => {
    const result = calculateScenario([], referenceData)

    expect(result.totalKgCO2e).toBe(0)
  })

  // Test 4: Negative quantity
  it('rejects negative quantity', () => {
    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: -1, unit: 'kg' }],
      referenceData
    )).toThrow()
  })

  // Test 5: Unknown activity
  it('rejects unknown activity', () => {
    expect(() => calculateScenario(
      [{ factorId: 'unknown', quantity: 2, unit: 'kg' }],
      referenceData
    )).toThrow()
  })

  // Test 6: Wrong unit
  it('rejects wrong unit', () => {
    expect(() => calculateScenario(
      [{ factorId: 'bus', quantity: 10, unit: 'km' }],
      referenceData
    )).toThrow()
  })

  // Test 7: Infinity quantity
  it('rejects Infinity quantity', () => {
    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: Infinity, unit: 'kg' }],
      referenceData
    )).toThrow()
  })

})
