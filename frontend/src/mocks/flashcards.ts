// Placeholder data shaped like future API responses (see docs/blueprint.md section 9).
// The real scheduler will return due cards and compute next intervals server-side —
// this only mimics the shape so the review UI has something to render.

import type { FlashcardReviewItem, ReviewRating } from '../types/flashcards'

export const mockFlashcardQueueLength = 8

export const mockFlashcard: FlashcardReviewItem = {
  id: 'sich-gewoehnen-an',
  word: 'sich gewöhnen an',
  partOfSpeech: 'Verb expression',
  exampleSentence: 'Ich muss mich noch an das neue Leben gewöhnen.',
  highlightedForm: 'gewöhnen',
  meaning: 'to get used to',
  meaningTranslation: 'I still have to get used to the new life.',
  grammarNote: 'sich gewöhnen an + accusative',
}

export const mockRatingIntervals: Record<ReviewRating, string> = {
  again: '1 min',
  hard: '1 day',
  good: '3 days',
  easy: '7 days',
}

export const mockSessionSummary = {
  cardsReviewed: 8,
  sessionMinutes: 4,
  rememberedCount: 6,
  ratingCounts: { again: 1, hard: 1, good: 5, easy: 1 } satisfies Record<ReviewRating, number>,
}
