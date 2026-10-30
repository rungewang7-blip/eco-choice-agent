import { describe, it, expect } from 'vitest'
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
    }
  ]
}

describe('F2 Validation Tests', () => {

  it('rejects negative emission factor', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = -5

    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      data
    )).toThrow('Invalid emission factor')
  })

  it('rejects NaN emission factor', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = NaN

    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      data
    )).toThrow('Invalid emission factor')
  })

  it('rejects Infinity emission factor', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = Infinity

    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      data
    )).toThrow('Invalid emission factor')
  })

  it('allows zero emission factor', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = 0

    const result = calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      data
    )

    expect(result.totalKgCO2e).toBe(0)
  })

  it('rejects emission multiplication overflow', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = 1e308

    expect(() => calculateScenario(
      [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
      data
    )).toThrow('Invalid emission')
  })

  it('rejects total emission overflow', () => {
    const data = structuredClone(referenceData)
    data.factors[0]!.kgCO2ePerUnit = 1e308

    expect(() => calculateScenario(
      [
        { factorId: 'beef', quantity: 1, unit: 'kg' },
        { factorId: 'beef', quantity: 1, unit: 'kg' }
      ],
      data
    )).toThrow('Invalid total emission')
  })

})