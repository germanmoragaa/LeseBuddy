// Remembers which decks were picked the last time a word was saved, so the deck picker in
// WordDetailPanel can preselect them next time. Best-effort only: localStorage can throw
// (private browsing, blocked site data, quota) or simply be empty, and losing this convenience
// is harmless, so every access is guarded rather than allowed to break saving a word.
const STORAGE_KEY = 'lesebuddy:last-used-deck-ids'

export function readLastUsedDeckIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === 'string') : []
  } catch {
    return []
  }
}

export function writeLastUsedDeckIds(deckIds: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(deckIds))
  } catch {
    // Dropped silently - see the file-level comment.
  }
}
