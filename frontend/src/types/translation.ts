// Mirrors the backend's TranslateRequest/TranslateResponse schemas exactly.
export interface TranslatePayload {
  start: number
  end: number
  include_sentence?: boolean
}

export interface TranslateResult {
  selection_translation: string
  sentence_translation: string | null
  quota_warning: string | null
  source: 'machine_translation'
}
