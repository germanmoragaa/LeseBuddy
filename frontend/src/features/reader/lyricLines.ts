import type { Token } from '../../types/analysis'

// For songs, a selection must stay inside one lyric line (newline-delimited) — the backend
// rejects anything else with a 422 (backend/app/services/selection.py). This maps each token
// to the 0-based line it starts on, so useTokenSelection can snap a selection to one line
// before it's ever sent. Token offsets are code points, so the text is walked by code point
// (Array.from), never by UTF-16 index.
export function lineIndexByToken(originalText: string, tokens: Token[]): number[] {
  const codePoints = Array.from(originalText)
  const newlinesBefore = new Array<number>(codePoints.length + 1)
  let count = 0
  for (let i = 0; i < codePoints.length; i++) {
    newlinesBefore[i] = count
    if (codePoints[i] === '\n') count++
  }
  newlinesBefore[codePoints.length] = count
  return tokens.map((token) => newlinesBefore[Math.min(token.start, codePoints.length)])
}
