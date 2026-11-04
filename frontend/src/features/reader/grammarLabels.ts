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
// entirely rather than showing an empty "Detected: " string.
export function formatMorph(morph: Record<string, string>): string | null {
  const values = Object.values(morph).map((value) => MORPH_VALUE_LABELS[value] ?? value)
  if (values.length === 0) return null
  return `Detected: ${values.join(', ')}`
}
