import { describe, expect, it } from 'vitest'

import { fmtCop, fmtCopDecimals, normalizeAmount } from '@/lib/money'

describe('fmtCop', () => {
  it.each([
    ['0', '$0'],
    ['1234567', '$1.234.567'],
    ['1234567.50', '$1.234.568'],
    ['-85000', '-$85.000'],
    [999.4, '$999'],
  ])('%s -> %s', (input, expected) => {
    expect(fmtCop(input)).toBe(expected)
  })

  it('treats unparseable input as zero', () => {
    expect(fmtCop('abc')).toBe('$0')
  })
})

describe('fmtCopDecimals', () => {
  it.each([
    ['0.00', '$0,00'],
    ['383333.34', '$383.333,34'],
    ['1200000.00', '$1.200.000,00'],
    ['-708000.05', '-$708.000,05'],
    ['12.99', '$12,99'],
  ])('%s -> %s', (input, expected) => {
    expect(fmtCopDecimals(input)).toBe(expected)
  })
})

describe('normalizeAmount', () => {
  it.each([
    ['1500000', '1500000.00'],
    ['1.500.000', '1500000.00'], // dots as thousands (CO)
    ['1.500', '1500.00'], // 3 digits after a single dot = thousands
    ['1.50', '1.50'], // 2 digits = decimals
    ['1500000,50', '1500000.50'], // comma as decimal
    ['1.500.000,50', '1500000.50'], // CO format
    ['1,500.50', '1500.50'], // US format
    ['$ 2.000', '2000.00'],
    ['0.500', '0.50'], // leading zero: decimal, not thousands
  ])('%s -> %s', (input, expected) => {
    expect(normalizeAmount(input)).toBe(expected)
  })

  it('returns non-numeric input unchanged so the API can reject it', () => {
    expect(normalizeAmount('doce mil')).toBe('docemil')
  })
})
