import { Layers, Plus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { useCreateDeck, useDecks, useDeleteDeck, useRenameDeck } from '../decks/deckHooks'
import { useReviewSummary } from './useReviewSummary'

export function FlashcardsStart() {
  const navigate = useNavigate()
  const decksQuery = useDecks()
  const summaryQuery = useReviewSummary()
  const createDeckMutation = useCreateDeck()
  const renameDeckMutation = useRenameDeck()
  const deleteDeckMutation = useDeleteDeck()

  const [newDeckName, setNewDeckName] = useState('')
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  function startSession(deckId: string) {
    navigate(`/app/flashcards?deck=${deckId}`)
  }

  function handleCreate() {
    const trimmed = newDeckName.trim()
    if (!trimmed) return
    createDeckMutation.mutate({ name: trimmed }, { onSuccess: () => setNewDeckName('') })
  }

  function startRenaming(deckId: string, currentName: string) {
    setRenamingId(deckId)
    setRenameValue(currentName)
  }

  function saveRename(deckId: string) {
    const trimmed = renameValue.trim()
    if (!trimmed) return
    renameDeckMutation.mutate(
      { deckId, payload: { name: trimmed } },
      { onSuccess: () => setRenamingId(null) },
    )
  }

  function handleDelete(deckId: string, name: string) {
    const confirmed = window.confirm(
      `Delete "${name}"? Your saved words and their review progress are kept — only the deck grouping is removed.`,
    )
    if (confirmed) deleteDeckMutation.mutate(deckId)
  }

  const decks = decksQuery.data?.items ?? []

  return (
    <div className="min-h-screen bg-[#f4f2ec] px-6 py-10">
      <div className="mx-auto mb-8 flex max-w-[820px] items-start justify-between">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Daily review
          </span>
          <h1 className="my-1.5 text-[28px] tracking-tight">Flashcards</h1>
          <p className="m-0 text-[13px] text-muted">
            Review everything at once, or focus on one deck.
          </p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/app')}>
          Back to dashboard
        </Button>
      </div>

      <div className="mx-auto max-w-[820px]">
        <button
          type="button"
          onClick={() => startSession('all')}
          className="mb-3 flex w-full items-center justify-between rounded-md border border-line bg-white px-5 py-4 text-left transition hover:-translate-y-px hover:bg-[#fdfdfa]"
        >
          <span className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-surface-mint text-brand">
              <Layers size={18} aria-hidden="true" />
            </span>
            <span>
              <strong className="block text-[14px]">All cards</strong>
              <small className="text-[10px] text-muted">Every word you've saved</small>
            </span>
          </span>
          <span className="text-[11px] text-muted">
            {summaryQuery.data?.due_count ?? 0} due · {summaryQuery.data?.total_cards ?? 0} total
          </span>
        </button>

        {decksQuery.isPending && (
          <p className="px-5 py-6 text-center text-sm text-muted">Loading your decks…</p>
        )}
        {decksQuery.isError && (
          <p className="px-5 py-6 text-center text-sm text-danger" role="alert">
            Couldn't load your decks.
          </p>
        )}

        {decks.length > 0 && (
          <Card className="mb-4 overflow-hidden">
            {decks.map((deck) => (
              <div
                key={deck.id}
                className="flex min-h-[64px] items-center gap-3 border-b border-line px-5 py-3 last:border-b-0"
              >
                {renamingId === deck.id ? (
                  <div className="flex flex-1 items-center gap-2">
                    <input
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      aria-label={`Rename ${deck.name}`}
                      className="min-w-0 flex-1 rounded-sm border border-line px-2.5 py-1.5 text-[12px] text-ink"
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault()
                          saveRename(deck.id)
                        }
                      }}
                    />
                    <Button
                      variant="secondary"
                      onClick={() => saveRename(deck.id)}
                      disabled={renameDeckMutation.isPending}
                    >
                      Save
                    </Button>
                    <Button variant="ghost" onClick={() => setRenamingId(null)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => startSession(deck.id)}
                      className="flex-1 text-left"
                    >
                      <strong className="block text-[13px]">{deck.name}</strong>
                      <small className="text-[10px] text-muted">
                        {deck.due_count} due · {deck.total_count} total
                      </small>
                    </button>
                    <Button variant="ghost" onClick={() => startRenaming(deck.id, deck.name)}>
                      Rename
                    </Button>
                    <Button variant="ghost" onClick={() => handleDelete(deck.id, deck.name)}>
                      Delete
                    </Button>
                  </>
                )}
              </div>
            ))}
          </Card>
        )}

        <div className="flex gap-2">
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
            className="min-w-0 flex-1 rounded-sm border border-line bg-white px-3 py-2.5 text-[13px] text-ink"
          />
          <Button onClick={handleCreate} disabled={createDeckMutation.isPending || !newDeckName.trim()}>
            <Plus size={16} aria-hidden="true" /> Create deck
          </Button>
        </div>
        {createDeckMutation.isError && (
          <p className="mt-2 text-[11px] text-danger" role="alert">
            Couldn't create that deck. It may already exist.
          </p>
        )}
      </div>
    </div>
  )
}
