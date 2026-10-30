import { describe, it, expect, vi } from 'vitest'
import { getFactors } from '../src/api/factors'
import { calculateScenario } from '../src/engine/calculate'

describe('F2 Privacy Tests', () => {

  it('does not send scenario data to backend', async () => {
    const mockData = {
      factorVersion: '2026-10-f1',
      factors: [{
        id: 'beef',
        category: 'food',
        activity: 'Beef',
        unit: 'kg',
        kgCO2ePerUnit: 99.48,
        source: 'Test',
        sourceYear: 2026,
        sourceUrl: 'https://example.com',
        factorVersion: '2026-10-f1'
      }]
    }

    const mockFetch = vi.spyOn(globalThis, 'fetch')

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockData
    } as Response)

    try {
      const referenceData = await getFactors()

      const result = calculateScenario(
        [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
        referenceData
      )

      expect(result.totalKgCO2e).toBeCloseTo(198.96)

      expect(mockFetch).toHaveBeenCalledTimes(1)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/factors'
      )
    } finally {
      mockFetch.mockRestore()
    }
  })
})