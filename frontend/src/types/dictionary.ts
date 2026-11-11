// Mirrors the backend's DictionaryLookupResponse/DictionaryEntryRead schemas exactly.
export interface DictionaryEntry {
  pos: string
  gender: string | null
  plural_only: boolean
  plural: string | null
  // Nominative article (der/die/das) derived server-side from gender, or "die" for a
  // plurale-tantum noun with no gender at all (e.g. "Eltern") — never derive this again on
  // the frontend, it's already resolved.
  article: 'der' | 'die' | 'das' | null
  glosses: string[]
  source_label: 'dictionary'
}

export interface DictionaryLookupResult {
  lemma: string
  pos_detected: string
  is_separable_verb: boolean
  entry: DictionaryEntry | null
}
