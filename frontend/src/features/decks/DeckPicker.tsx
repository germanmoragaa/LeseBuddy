import { useState } from 'react'

import { Button } from '../../components/Button'
import type { Deck } from '../../types/deck'

interface DeckPickerProps {
  decks: Deck[]
  selectedDeckIds: string[]
  onToggle: (deckId: string) => void
  onCreateDeck: (name: string) => void
  isCreating?: boolean
  disabled?: boolean
}

// Shared between WordDetailPanel's save flow and Vocabulary's bulk "Add to deck" action - a
// checkbox list of existing decks plus an inline "New deck" field, so creating a deck never
// requires leaving whichever flow the user is already in.
export function DeckPicker({
  decks,
  selectedDeckIds,
  onToggle,
  onCreateDeck,
  isCreating = false,
  disabled = false,
}: DeckPickerProps) {
  const [newDeckName, setNewDeckName] = useState('')

  function handleCreate() {
    const trimmed = newDeckName.trim()
    if (!trimmed) return
    onCreateDeck(trimmed)
    setNewDeckName('')
  }

  return (
    <div>
      {decks.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {decks.map((deck) => (
            <li key={deck.id}>
              <label className="flex items-center gap-2 text-[12px] text-ink">
                <input
                  type="checkbox"
                  checked={selectedDeckIds.includes(deck.id)}
                  onChange={() => onToggle(deck.id)}
                  disabled={disabled}
                />
                {deck.name}
              </label>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-2 flex gap-1.5">
        <input
          value={newDeckName}
          onChange={(event) => setNewDeckName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              handleCreate()
            }
          }}
          placeholder="New deck name"
          aria-label="New deck name"
          className="min-w-0 flex-1 rounded-sm border border-line px-2.5 py-1.5 text-[12px] text-ink"
        />
        <Button
          variant="secondary"
          onClick={handleCreate}
          disabled={isCreating || !newDeckName.trim()}
        >
          Add
        </Button>
      </div>
    </div>
  )
}
