/**
 * Colombian peso formatting, ported from the backend's money.py.
 * Amounts arrive as fixed-precision strings from the API.
 */

const parseDecimal = (value: string | number): number => {
  if (typeof value === 'number') return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/** Format an amount as $1.234.567 (thousands with dots, no decimals). */
export function fmtCop(value: string | number): string {
  const amount = parseDecimal(value)
  const sign = amount < 0 ? '-' : ''
  const rounded = Math.round(Math.abs(amount))
  const withSeparators = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}$${withSeparators}`
}

/** Format an amount with decimals: $1.234.567,89. */
export function fmtCopDecimals(value: string | number): string {
  const amount = parseDecimal(value)
  const sign = amount < 0 ? '-' : ''
  const abs = Math.abs(amount)
  const whole = Math.trunc(abs)
  const decimals = Math.round((abs - whole) * 100)
  const wholeText = whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  const decimalsText = decimals.toString().padStart(2, '0')
  return `${sign}$${wholeText},${decimalsText}`
}

/** Normalize a user-typed amount to a fixed-precision string the API accepts. */
export function normalizeAmount(input: string): string {
  const cleaned = input.trim().replace(/[$\s\u00a0]/g, '')
  const negative = cleaned.startsWith('-')
  const body = cleaned.replace(/^-/, '')
  if (!/^[0-9.,]+$/.test(body)) return cleaned

  let normalized: string
  if (body.includes('.') && body.includes(',')) {
    // Last separator wins as decimal separator (CO/US mixed formats)
    normalized =
      body.lastIndexOf('.') > body.lastIndexOf(',')
        ? body.replace(/,/g, '')
        : body.replace(/\./g, '').replace(',', '.')
  } else if (body.includes(',')) {
    normalized = normalizeSingleSeparator(body, ',')
  } else if (body.includes('.')) {
    normalized = normalizeSingleSeparator(body, '.')
  } else {
    normalized = body
  }

  const value = Number(normalized)
  if (!Number.isFinite(value)) return cleaned
  return (negative ? '-' : '') + value.toFixed(2)
}

function normalizeSingleSeparator(body: string, sep: string): string {
  const parts = body.split(sep)
  if (parts.length > 2) return body.replaceAll(sep, '')
  if (parts.length === 2 && parts[1].length === 3 && parts[0] !== '0') {
    return body.replace(sep, '')
  }
  return body.replace(sep, '.')
}
