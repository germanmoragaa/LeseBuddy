import { describe, expect, it } from 'vitest'

import { getGermanGreeting } from './greeting'

describe('getGermanGreeting', () => {
  it('returns Guten Morgen before noon', () => {
    expect(getGermanGreeting(new Date(2026, 0, 1, 8, 0))).toBe('Guten Morgen')
    expect(getGermanGreeting(new Date(2026, 0, 1, 11, 59))).toBe('Guten Morgen')
  })

  it('returns Guten Tag from noon until 6pm', () => {
    expect(getGermanGreeting(new Date(2026, 0, 1, 12, 0))).toBe('Guten Tag')
    expect(getGermanGreeting(new Date(2026, 0, 1, 17, 59))).toBe('Guten Tag')
  })

  it('returns Guten Abend from 6pm onward', () => {
    expect(getGermanGreeting(new Date(2026, 0, 1, 18, 0))).toBe('Guten Abend')
    expect(getGermanGreeting(new Date(2026, 0, 1, 23, 30))).toBe('Guten Abend')
  })
})
