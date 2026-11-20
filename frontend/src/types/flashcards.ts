// Mirrors backend/app/schemas/review.py exactly (snake_case, matching the JSON the API
// returns).
import type { Meaning } from './vocabulary'

export type ReviewRating = 'again' | 'hard' | 'good' | 'easy'

export interface FlashcardFront {
  // Dictionary-style headword built server-side: "der Schein, -e" for nouns (article +
  // plural notation), the infinitive for verbs, the expression for phrases.
  display: string
  /** @deprecated use `display` */
  display_form: string
  part_of_speech: string
  // Only present for nouns — rendered as the der/die/das article (see grammarLabels.ts).
  gender: string | null
}

export interface CardSong {
  title: string
  artist: string
  cover_url: string | null
  cover_thumbnail_url?: string | null
}

export interface CardExample {
  line: string
  translation: string | null
  // Code-point offsets of the word within `line` — go through CodePointIndex, never slice.
  highlight_start: number | null
  highlight_end: number | null
  song: CardSong | null
}

export interface FlashcardBack {
  // All meanings in order; the first (usually the contextual machine one) is emphasized.
  meanings: Meaning[]
  example: CardExample | null
  /** @deprecated use `meanings` */
  translation: string | null
  /** @deprecated use `meanings` */
  glosses: string[]
  part_of_speech: string
  /** @deprecated use `example.line` */
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
