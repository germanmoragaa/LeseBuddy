// Mirrors the backend's DictionaryLookupResponse/DictionaryEntryRead schemas exactly.
export interface DictionaryEntry {
  pos: string
  gender: string | null
  plural: string | null
  glosses: string[]
  source_label: 'dictionary'
}

export interface DictionaryLookupResult {
  lemma: string
  pos_detected: string
  is_separable_verb: boolean
  entry: DictionaryEntry | null
}
