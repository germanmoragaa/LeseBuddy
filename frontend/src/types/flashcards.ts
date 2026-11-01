export type ReviewRating = 'again' | 'hard' | 'good' | 'easy'

export interface FlashcardReviewItem {
  id: string
  word: string
  partOfSpeech: string
  exampleSentence: string
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
