export type ReviewRating = 'again' | 'hard' | 'good' | 'easy'

export interface FlashcardReviewItem {
  id: string
  word: string
  partOfSpeech: string
  exampleSentence: string
  /** The inflected substring of exampleSentence to highlight — may differ from the dictionary form `word`. */
  highlightedForm: string
  meaning: string
  meaningTranslation: string
  grammarNote?: string
}

export interface ReviewSessionSummary {
  cardsReviewed: number
  sessionMinutes: number
  rememberedCount: number
  ratingCounts: Record<ReviewRating, number>
}
