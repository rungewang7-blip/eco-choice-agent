export function formatEmission(value: number): string {

  if (!Number.isFinite(value) || value < 0) {
    throw new Error('Invalid emission value')
  }

  if (value === 0) {
    return '0'
  }

  return Number(value.toPrecision(2)).toLocaleString('en-US', {
    minimumSignificantDigits: 2,
    maximumSignificantDigits: 2
  })
}
