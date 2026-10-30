import { describe, it, expect, vi } from 'vitest'
import { getFactors } from '../src/api/factors'
import { calculateScenario } from '../src/engine/calculate'

describe('F1 and F2 Integration', () => {

  it('calculates emissions using F1 API data', async () => {

    // Simulate the F1 API response
    const mockData = {
      factorVersion: '2026-10-f1',
      factors: [
        {
          id: 'beef',
          category: 'food',
          activity: 'Beef (beef herd)',
          unit: 'kg',
          kgCO2ePerUnit: 99.48,
          source: 'Poore and Nemecek 2018',
          sourceYear: 2018,
          sourceUrl: 'https://ourworldindata.org',
          factorVersion: '2026-10-f1'
        }
      ]
    }

    // Replace fetch with a simulated response
    const mockFetch = vi.spyOn(globalThis, 'fetch')

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    } as Response)

    try {
      // Step 1: Get factors through the API function
      const referenceData = await getFactors()

      // Step 2: Calculate emissions
      const result = calculateScenario(
        [{ factorId: 'beef', quantity: 2, unit: 'kg' }],
        referenceData
      )

      // Step 3: Check the result
      expect(result.totalKgCO2e).toBeCloseTo(198.96)

      // Step 4: Check the factor version
      expect(result.factorVersion).toBe('2026-10-f1')

      // Step 5: Check that the API uses GET
      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/factors'
      )

      // Step 6: Check that only one request was made
      expect(mockFetch).toHaveBeenCalledTimes(1)

    } finally {
      mockFetch.mockRestore()
    }
  })

})