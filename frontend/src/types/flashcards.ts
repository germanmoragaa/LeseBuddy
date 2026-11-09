// Mirrors backend/app/schemas/review.py exactly (snake_case, matching the JSON the API
// returns).
export type ReviewRating = 'again' | 'hard' | 'good' | 'easy'

export interface FlashcardFront {
  display_form: string
  part_of_speech: string
  // Only present for nouns — rendered as the der/die/das article (see grammarLabels.ts).
  gender: string | null
}

export interface FlashcardBack {
  translation: string | null
  glosses: string[]
  part_of_speech: string
  context_sentence: string | null
}

export interface DueFlashcard {
  id: string
  vocabulary_item_id: string
  due_at: string
  front: FlashcardFront
  back: FlashcardBack
  preview: Record<ReviewRating, number>
}

export interface DueFlashcardsResponse {
  items: DueFlashcard[]
}

export interface ReviewSummary {
  due_count: number
  next_due_at: string | null
  total_cards: number
}

export interface ReviewSubmitPayload {
  flashcard_id: string
  rating: ReviewRating
  client_review_id?: string
}

export interface ReviewSubmitResult {
  flashcard_id: string
  rating: ReviewRating
  ease_factor: number
  interval_days: number
  due_at: string
  reviewed_at: string
}
