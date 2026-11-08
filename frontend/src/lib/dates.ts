/**
 * Calendar dates as the user sees them (local time), in ISO form "YYYY-MM-DD".
 *
 * Never use `Date.toISOString()` for a calendar date: it converts to UTC, so
 * in Colombia (UTC-5) any time after 19:00 already reads as tomorrow.
 */
import type { Month } from '@/hooks/useMonth'

const pad = (n: number) => String(n).padStart(2, '0')

/** Local calendar date of `d` as "YYYY-MM-DD". */
export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Today's local date as "YYYY-MM-DD". */
export function todayISO(now: Date = new Date()): string {
  return toISODate(now)
}

/** Add `days` to an ISO date, in local time. */
export function addDaysISO(iso: string, days: number): string {
  const [year, month, day] = iso.split('-').map(Number)
  return toISODate(new Date(year, month - 1, day + days))
}

/**
 * Date proposed for a new movement while browsing `month`: today when it is
 * the current month (a purchase made now must not land in the future), the
 * 15th otherwise.
 */
export function defaultMovementDate(month: Month, now: Date = new Date()): string {
  if (month.year === now.getFullYear() && month.month === now.getMonth() + 1) {
    return toISODate(now)
  }
  return `${month.year}-${pad(month.month)}-15`
}
