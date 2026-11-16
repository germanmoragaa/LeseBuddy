import { describe, expect, it } from 'vitest'

import { formatRelativeTime } from './relativeTime'

describe('formatRelativeTime', () => {
  const now = new Date('2026-01-10T12:00:00Z')

  it('shows "just now" for less than a minute ago', () => {
    expect(formatRelativeTime('2026-01-10T11:59:30Z', now)).toBe('just now')
  })

  it('shows minutes ago for less than an hour', () => {
    expect(formatRelativeTime('2026-01-10T11:45:00Z', now)).toBe('15 minutes ago')
  })

  it('uses singular "minute" for exactly one minute', () => {
    expect(formatRelativeTime('2026-01-10T11:59:00Z', now)).toBe('1 minute ago')
  })

  it('shows hours ago for less than a day', () => {
    expect(formatRelativeTime('2026-01-10T10:00:00Z', now)).toBe('2 hours ago')
  })

  it('shows days ago for less than a week', () => {
    expect(formatRelativeTime('2026-01-08T12:00:00Z', now)).toBe('2 days ago')
  })

  it('falls back to an absolute date a week or more in the past', () => {
    expect(formatRelativeTime('2025-12-01T12:00:00Z', now)).toBe('1 Dec')
  })
})
