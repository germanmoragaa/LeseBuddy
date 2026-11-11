// Mirrors the backend's vocabulary schemas exactly. No spaced-repetition fields here (no
// `status`/`nextReview`) — flashcards are a separate, not-yet-built step; this type only
// carries what the real backend actually stores.
export interface GrammarMetadata {
  gender?: string
  article?: string
  plural?: string
  [key: string]: unknown
}

export interface VocabularyOccurrence {
  id: string
  article_id: string
  start_offset: number
  end_offset: number
  context_sentence: string
  created_at: string
}

export interface VocabularyItem {
  id: string
  lemma: string
  display_form: string
  meaning: string | null
  translation: string | null
  part_of_speech: string
  grammar_metadata: GrammarMetadata
  notes: string | null
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
}

export interface VocabularyOccurrenceSummary {
  start_offset: number
  end_offset: number
  vocabulary_item_id: string
}

export interface VocabularyPatchPayload {
  meaning?: string | null
  translation?: string | null
  notes?: string | null
}
