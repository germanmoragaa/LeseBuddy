import type { Meaning, VocabularyItemDetail } from '../../types/vocabulary'

// Items saved before `meanings` existed only have the deprecated fields — show those.
export function displayMeanings(item: VocabularyItemDetail): Meaning[] {
  if (item.meanings.length > 0) return item.meanings
  const legacy: Meaning[] = []
  if (item.translation) legacy.push({ text: item.translation, source: 'machine' })
  if (item.meaning && item.meaning !== item.translation) {
    legacy.push({ text: item.meaning, source: 'dictionary' })
  }
  return legacy
}

// The card example: the chosen occurrence, else the first one saved (occurrences arrive
// newest first, so that's the last one) — mirrors review_service.load_card_examples.
export function effectiveExampleId(item: VocabularyItemDetail): string | null {
  if (item.example_occurrence_id) return item.example_occurrence_id
  return item.occurrences[item.occurrences.length - 1]?.id ?? null
}
