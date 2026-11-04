import { describe, expect, it } from 'vitest'

import { CodePointIndex } from './textOffsets'

describe('CodePointIndex', () => {
  it('matches raw slicing for text with no astral characters', () => {
    const text = 'Der große Käfer läuft über die Straße.'
    const index = new CodePointIndex(text)

    expect(index.slice(text, 0, 3)).toBe('Der')
    expect(index.slice(text, 4, 9)).toBe('große')
  })

  it('slices correctly for a token positioned after an emoji earlier in the text', () => {
    const text = 'Ich liebe 🐶 Hunde.'
    // Code-point offsets (what the backend would send): "Hunde" starts at code point 12
    // (I-c-h-sp-l-i-e-b-e-sp-🐶-sp = 12 code points before it) and ends at 17.
    const wordStart = 12
    const wordEnd = 17
    const index = new CodePointIndex(text)

    expect(index.slice(text, wordStart, wordEnd)).toBe('Hunde')
    // Demonstrates the exact bug this helper exists to prevent: naively slicing with the raw
    // backend (code-point) offset via the native UTF-16-indexed `.slice()` gives the wrong
    // substring once an astral character (here, the dog emoji, a surrogate pair) appears
    // earlier in the text.
    expect(text.slice(wordStart, wordEnd)).not.toBe('Hunde')
  })

  it('round-trips every token boundary for a text containing an emoji', () => {
    const text = 'Vorher 🐶 danach.'
    const index = new CodePointIndex(text)
    const codePoints = Array.from(text)

    for (let start = 0; start < codePoints.length; start++) {
      for (let end = start; end <= codePoints.length; end++) {
        expect(index.slice(text, start, end)).toBe(codePoints.slice(start, end).join(''))
      }
    }
  })
})
