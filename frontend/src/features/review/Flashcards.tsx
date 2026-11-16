import { useSearchParams } from 'react-router'

import { FlashcardsSession } from './FlashcardsSession'
import { FlashcardsStart } from './FlashcardsStart'

// No ?deck= at all -> the start screen (pick "All cards" or a deck). ?deck=all -> an
// unfiltered session (the sentinel, not a real deck id). ?deck=<uuid> -> a session filtered
// to that one deck.
export function Flashcards() {
  const [searchParams] = useSearchParams()
  const deckParam = searchParams.get('deck')

  if (deckParam === null) {
    return <FlashcardsStart />
  }
  return <FlashcardsSession deckId={deckParam === 'all' ? undefined : deckParam} />
}
