// Mirrors the backend's vocabulary schemas exactly. No spaced-repetition fields here (no
// `status`/`nextReview`) — flashcards are a separate, not-yet-built step; this type only
// carries what the real backend actually stores.
export interface GrammarMetadata {
  gender?: string
  article?: string
  plural?: string
  plural_only?: boolean
  [key: string]: unknown
}

export type MeaningSource = 'machine' | 'dictionary'

export interface Meaning {
  text: string
  source: MeaningSource
  sense_label?: string | null
}

export interface VocabularyOccurrence {
  id: string
  article_id: string
  start_offset: number
  end_offset: number
  /** @deprecated use `context_line` */
  context_sentence: string
  // The lyric line (songs) or sentence (texts) the word was saved from.
  context_line: string | null
  context_translation: string | null
  // The line translation failed at save time — retry via retryOccurrenceTranslation.
  needs_translation: boolean
  created_at: string
}

export interface VocabularyItem {
  id: string
  lemma: string
  display_form: string
  /** @deprecated use `meanings` */
  meaning: string | null
  /** @deprecated use `meanings` */
  translation: string | null
  meanings: Meaning[]
  // The occurrence shown on the flashcard; null falls back to the first one saved.
  example_occurrence_id: string | null
  part_of_speech: string
  grammar_metadata: GrammarMetadata
  notes: string | null
  deck_ids: string[]
  created_at: string
  updated_at: string
}

export interface VocabularyItemDetail extends VocabularyItem {
  occurrences: VocabularyOccurrence[]
}

export interface VocabularyListResponse {
  items: VocabularyItem[]
  total: number
  page: number
  page_size: number
}

export interface VocabularySaveResponse {
  item: VocabularyItem
  already_saved: boolean
  // DeepL failed during the save; the word is saved without its translation.
  translation_pending: boolean
  occurrence_id: string | null
}

export interface VocabularyOccurrenceSummary {
  start_offset: number
  end_offset: number
  vocabulary_item_id: string
}

export interface VocabularyPatchPayload {
  /** @deprecated use `meanings` */
  meaning?: string | null
  /** @deprecated use `meanings` */
  translation?: string | null
  notes?: string | null
  meanings?: Meaning[]
  example_occurrence_id?: string | null
}

export interface OccurrencePatchPayload {
  context_translation: string | null
}
