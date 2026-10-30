export function formatEmission(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error('Invalid emission value')
  }

  if (value === 0) {
    return '0'
  }

  if (value < 0.01) {
    return Number(value.toPrecision(2)).toLocaleString('en-US', {
      maximumFractionDigits: 20
    })
  }

  return value.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })
}