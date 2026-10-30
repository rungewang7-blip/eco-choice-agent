
/* @vitest-environment jsdom */

import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import ScenarioEditor from '../src/ScenarioEditor.vue'
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
      source: 'test',
      sourceYear: 2026,
      sourceUrl: 'https://example.com/beef',
      factorVersion: '2026-10-f1'
    },
    {
      id: 'bus',
      category: 'transport',
      activity: 'Bus',
      unit: 'passenger.km',
      kgCO2ePerUnit: 0.10385,
      source: 'test',
      sourceYear: 2026,
      sourceUrl: 'https://example.com/bus',
      factorVersion: '2026-10-f1'
    }
  ]
}

let fetchMock: ReturnType<typeof vi.fn>

async function createEditor() {
  const wrapper = mount(ScenarioEditor)
  await flushPromises()
  return wrapper
}

async function addActivity(wrapper: Awaited<ReturnType<typeof createEditor>>) {
  const button = wrapper.findAll('button')
    .find(b => b.text() === 'Add activity')

  if (!button) throw new Error('Add activity button missing')
  await button.trigger('click')
}

beforeEach(() => {
  fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => referenceData
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('F3 ScenarioEditor', () => {
  it('loads public factors and displays version', async () => {
    const wrapper = await createEditor()

    expect(wrapper.text()).toContain('2026-10-f1')
    expect(wrapper.text()).toContain('Add activity')
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      '/factors'
    )

    wrapper.unmount()
  })

  it('adds and removes an activity', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    expect(wrapper.findAll('.activity-row')).toHaveLength(1)

    await wrapper.find('.activity-row button').trigger('click')
    expect(wrapper.findAll('.activity-row')).toHaveLength(0)

    wrapper.unmount()
  })

  it('updates unit when factor changes', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('select').setValue('bus')

    expect(wrapper.text()).toContain('Quantity (passenger.km)')

    wrapper.unmount()
  })

  it('calculates beef emissions using F2', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('input').setValue('2')

    expect(wrapper.text()).toContain('200 kgCO₂e')

    wrapper.unmount()
  })

  it('calculates food and transport categories', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('input').setValue('2')

    await addActivity(wrapper)

    const rows = wrapper.findAll('.activity-row')
    await rows[1]!.find('select').setValue('bus')
    await rows[1]!.find('input').setValue('10')

    const result = wrapper.find('section').text()

    expect(result).toContain('Total:')
    expect(result).toContain('Food: 200 kgCO₂e')
    expect(result).toContain('Transport: 1.0 kgCO₂e')

    wrapper.unmount()
  })

  it('rejects negative quantities', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('input').setValue('-3')

    expect(wrapper.text()).toContain(
      'Quantity must be a non-negative number'
    )
    expect(wrapper.find('section').exists()).toBe(false)

    wrapper.unmount()
  })

  it('rejects empty quantities', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('input').setValue('')

    expect(wrapper.text()).toContain(
      'Quantity must be a non-negative number'
    )

    wrapper.unmount()
  })

  it('shows an error when F1 request fails', async () => {
    fetchMock.mockRejectedValueOnce(new Error('Network error'))

    const wrapper = await createEditor()

    expect(wrapper.text()).toContain(
      'Failed to load carbon factors'
    )

    wrapper.unmount()
  })

  it('does not upload scenario data', async () => {
    const wrapper = await createEditor()

    await addActivity(wrapper)
    await wrapper.find('input').setValue('2')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      '/factors'
    )

    wrapper.unmount()
  })
})
