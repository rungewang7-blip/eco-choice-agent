import { describe, it, expect } from 'vitest'
import { formatEmission } from '../src/engine/format'
import { calculateScenario } from '../src/engine/calculate'
import type { FactorsResponse } from '../src/engine/types'

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
    },
    {
      id: 'paper',
      category: 'items',
      activity: 'Paper',
      unit: 'kg',
      kgCO2ePerUnit: 1.3450779,
      source: 'DESNZ 2025',
      sourceYear: 2025,
      sourceUrl: 'https://www.gov.uk',
      factorVersion: '2026-10-f1'
    }
  ]
}

describe('F2 Precision Tests', () => {

  // Test 1: Keep full calculation precision
  it('keeps full precision during calculation', () => {
    const result = calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      referenceData
    )

    expect(result.totalKgCO2e).toBeCloseTo(198.96)
  })

  // Test 2: Round only for display
  it('formats beef emissions to 2 significant figures', () => {
    expect(formatEmission(198.96)).toBe('200')
  })

  // Test 3: Preserve trailing zero
  it('preserves trailing zero for 1.0', () => {
    expect(formatEmission(1.0385)).toBe('1.0')
  })

  // Test 4: Format small values
  it('formats small emissions', () => {
    expect(formatEmission(0.004567)).toBe('0.0046')
  })

  // Test 5: Format paper emissions
  it('formats paper emissions', () => {
    expect(formatEmission(1.3450779)).toBe('1.3')
  })

  // Test 6: Handle zero
  it('formats zero', () => {
    expect(formatEmission(0)).toBe('0')
  })

  // Test 7: Keep precision before adding totals
  it('does not round individual emissions before summing', () => {
    const result = calculateScenario(
      [
        { factorId: 'beef', quantity: 2, unit: 'kg' },
        { factorId: 'bus', quantity: 10, unit: 'passenger.km' }
      ],
      referenceData
    )

    expect(result.totalKgCO2e).toBeCloseTo(199.9985)
    expect(formatEmission(result.totalKgCO2e)).toBe('200')
  })

  // Test 8: Reject invalid values
  it('rejects invalid emission values', () => {
    expect(() => formatEmission(-1)).toThrow('Invalid emission value')
    expect(() => formatEmission(Infinity)).toThrow('Invalid emission value')
    expect(() => formatEmission(NaN)).toThrow('Invalid emission value')
  })

})