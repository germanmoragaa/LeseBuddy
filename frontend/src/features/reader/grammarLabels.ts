// Learner-friendly display labels. The backend contract stays raw (UPOS tags, UD morph
// feature codes) — translating them into plain English is a presentation concern, not part
// of the API.
const POS_LABELS: Record<string, string> = {
  NOUN: 'Noun',
  PROPN: 'Noun',
  VERB: 'Verb',
  AUX: 'Verb',
  ADJ: 'Adjective',
  ADV: 'Adverb',
  ADP: 'Preposition',
  DET: 'Article/Determiner',
  PRON: 'Pronoun',
  CCONJ: 'Conjunction',
  SCONJ: 'Conjunction',
  NUM: 'Number',
  PART: 'Particle',
  PUNCT: 'Punctuation',
  SYM: 'Symbol',
  INTJ: 'Interjection',
}

export function posLabel(pos: string): string {
  return POS_LABELS[pos] ?? pos
}

const MORPH_VALUE_LABELS: Record<string, string> = {
  Fem: 'feminine',
  Masc: 'masculine',
  Neut: 'neuter',
  Nom: 'nominative',
  Gen: 'genitive',
  Dat: 'dative',
  Acc: 'accusative',
  Sing: 'singular',
  Plur: 'plural',
  Pres: 'present',
  Past: 'past',
}

// Returns null when there's nothing detected, so callers can skip rendering the line
// entirely rather than showing an empty "Detected: " string. `excludeGender` lets callers
// that render a separate dictionary-vs-detected gender line (see resolveGender below) avoid
// showing two contradicting gender values.
export function formatMorph(
  morph: Record<string, string>,
  options: { excludeGender?: boolean } = {},
): string | null {
  const entries = Object.entries(morph).filter(
    ([key]) => !(options.excludeGender && key === 'Gender'),
  )
  const values = entries.map(([, value]) => MORPH_VALUE_LABELS[value] ?? value)
  if (values.length === 0) return null
  return `Detected: ${values.join(', ')}`
}

const GENDER_ARTICLES: Record<string, string> = { Masc: 'der', Fem: 'die', Neut: 'das' }

// Used by the flashcard front (features/review/) to show "der Hund" rather than just "Hund".
export function genderArticle(gender: string | null): string | null {
  return gender ? GENDER_ARTICLES[gender] ?? null : null
}

export interface ResolvedGender {
  label: string
  source: 'dictionary' | 'detected'
}

// The dictionary's gender wins on disagreement (normalized to the same Fem/Masc/Neut codes
// at import time — see app/scripts/import_dictionary.py) since it's a verified lexical fact,
// not a per-sentence statistical guess. Returns null when neither source has a gender (e.g.
// the word isn't a noun).
export function resolveGender(
  detectedGender: string | undefined,
  dictionaryGender: string | null | undefined,
): ResolvedGender | null {
  if (dictionaryGender) {
    return { label: MORPH_VALUE_LABELS[dictionaryGender] ?? dictionaryGender, source: 'dictionary' }
  }
  if (detectedGender) {
    return { label: MORPH_VALUE_LABELS[detectedGender] ?? detectedGender, source: 'detected' }
  }
  return null
}
