import type { FlashcardBack } from '../../types/flashcards'
import type { Meaning } from '../../types/vocabulary'

// Older payloads (or items whose meanings were never filled) still carry the deprecated
// fields — fall back to them so no card ever renders an empty answer.
export function cardMeanings(back: FlashcardBack): Meaning[] {
  if (back.meanings.length > 0) return back.meanings
  const fallback: Meaning[] = []
  if (back.translation) fallback.push({ text: back.translation, source: 'machine' })
  for (const gloss of back.glosses) fallback.push({ text: gloss, source: 'dictionary' })
  return fallback
}

export function primaryMeaningText(back: FlashcardBack): string {
  return cardMeanings(back)[0]?.text ?? '—'
}
