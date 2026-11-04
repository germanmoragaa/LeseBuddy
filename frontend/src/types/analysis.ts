// Mirrors the backend's ArticleAnalysisResult schema exactly. Offsets are Unicode code
// points into the article's original_text — see src/lib/textOffsets.ts and
// docs/decisions/0003-nlp-pipeline.md before slicing text with them.
export interface Token {
  text: string
  start: number
  end: number
  whitespace_after: string
  is_punct: boolean
  is_space: boolean
  lemma: string
  pos: string
  // Statistically detected morphology (e.g. {"Gender": "Fem", "Number": "Sing"}) — a guess,
  // never a verified dictionary fact. Always render it labeled as "detected".
  morph: Record<string, string>
}

export interface Sentence {
  start: number
  end: number
}

export interface SeparableVerb {
  lemma: string
  verb_token_index: number
  particle_token_index: number
}

export interface ArticleAnalysis {
  analysis_version: number
  difficulty_estimate: number | null
  tokens: Token[]
  sentences: Sentence[]
  separable_verbs: SeparableVerb[]
}
