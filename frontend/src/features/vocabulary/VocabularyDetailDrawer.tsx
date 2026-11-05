import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { deleteVocabularyItem, getVocabularyItem, patchVocabularyItem } from '../../lib/api'
import type { VocabularyOccurrence } from '../../types/vocabulary'

interface VocabularyDetailDrawerProps {
  itemId: string
  onClose: () => void
}

const dangerButtonClassName =
  'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-sm border border-line bg-white px-4 text-[13px] font-bold text-danger transition hover:-translate-y-px hover:bg-danger/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:pointer-events-none disabled:opacity-50'

// Occurrence offsets are absolute into the article's text, not relative to the stored
// context_sentence snippet — so exact-offset highlighting isn't available here. A
// case-insensitive substring match against the saved display form is a reasonable
// approximation for drawing attention to the word within its sentence.
function highlightSentence(sentence: string, term: string) {
  const index = sentence.toLowerCase().indexOf(term.toLowerCase())
  if (index === -1) return sentence
  return (
    <>
      {sentence.slice(0, index)}
      <mark className="rounded-[2px] bg-accent-soft px-0.5">
        {sentence.slice(index, index + term.length)}
      </mark>
      {sentence.slice(index + term.length)}
    </>
  )
}

function OccurrenceRow({ occurrence, term }: { occurrence: VocabularyOccurrence; term: string }) {
  const navigate = useNavigate()
  return (
    <div className="border-b border-line py-4 last:border-b-0">
      <p className="text-[11px] leading-relaxed text-ink">
        {highlightSentence(occurrence.context_sentence, term)}
      </p>
      <button
        type="button"
        onClick={() => navigate(`/app/reader/${occurrence.article_id}`)}
        className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-bold text-action"
      >
        Open in article <ExternalLink size={14} aria-hidden="true" />
      </button>
    </div>
  )
}

export function VocabularyDetailDrawer({ itemId, onClose }: VocabularyDetailDrawerProps) {
  const queryClient = useQueryClient()
  const itemQuery = useQuery({
    queryKey: ['vocabulary-item', itemId],
    queryFn: () => getVocabularyItem(itemId),
  })

  const [isEditing, setIsEditing] = useState(false)
  const [meaning, setMeaning] = useState('')
  const [translation, setTranslation] = useState('')
  const [notes, setNotes] = useState('')

  function startEditing() {
    if (!itemQuery.data) return
    setMeaning(itemQuery.data.meaning ?? '')
    setTranslation(itemQuery.data.translation ?? '')
    setNotes(itemQuery.data.notes ?? '')
    setIsEditing(true)
  }

  const patchMutation = useMutation({
    mutationFn: () =>
      patchVocabularyItem(itemId, {
        meaning: meaning || null,
        translation: translation || null,
        notes: notes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocabulary-item', itemId] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteVocabularyItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
      onClose()
    },
  })

  function handleDelete() {
    if (window.confirm('Delete this word from your vocabulary? This cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  const item = itemQuery.data

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close vocabulary detail"
        onClick={onClose}
        className="absolute inset-0 w-full border-0 bg-black/30"
      />
      <aside className="absolute inset-y-0 right-0 w-full max-w-[440px] overflow-y-auto bg-white p-6 shadow-[-20px_0_60px_rgb(25_40_31_/_0.14)]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Vocabulary detail
          </span>
          <Button variant="icon" aria-label="Close vocabulary detail" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        {itemQuery.isPending && <p className="py-10 text-center text-sm text-muted">Loading…</p>}
        {itemQuery.isError && (
          <p className="py-10 text-center text-sm text-danger" role="alert">
            Couldn't load this word.
          </p>
        )}

        {item && (
          <>
            <div className="border-b border-line py-7">
              <small className="text-[9px] font-bold uppercase tracking-wide text-muted">
                {item.part_of_speech}
                {item.grammar_metadata.gender ? ` · ${item.grammar_metadata.gender}` : ''}
              </small>
              <h2 className="mb-1 mt-1.5 text-[32px] tracking-tight">{item.display_form}</h2>
              {item.grammar_metadata.plural && (
                <p className="text-[11px] text-muted">Plural: {item.grammar_metadata.plural}</p>
              )}
            </div>

            <div className="border-b border-line py-5">
              <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
                Meaning &amp; translation
              </span>
              {isEditing ? (
                <div className="flex flex-col gap-2">
                  <input
                    value={meaning}
                    onChange={(event) => setMeaning(event.target.value)}
                    placeholder="Meaning"
                    aria-label="Meaning"
                    className="rounded-sm border border-line px-2.5 py-2 text-[12px]"
                  />
                  <input
                    value={translation}
                    onChange={(event) => setTranslation(event.target.value)}
                    placeholder="Translation"
                    aria-label="Translation"
                    className="rounded-sm border border-line px-2.5 py-2 text-[12px]"
                  />
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Notes"
                    aria-label="Notes"
                    rows={3}
                    className="rounded-sm border border-line px-2.5 py-2 text-[12px]"
                  />
                  <div className="flex gap-2">
                    <Button
                      className="flex-1"
                      onClick={() => patchMutation.mutate()}
                      disabled={patchMutation.isPending}
                    >
                      {patchMutation.isPending ? 'Saving…' : 'Save changes'}
                    </Button>
                    <Button variant="secondary" className="flex-1" onClick={() => setIsEditing(false)}>
                      Cancel
                    </Button>
                  </div>
                  {patchMutation.isError && (
                    <p className="text-[11px] text-danger" role="alert">
                      Couldn't save your changes.
                    </p>
                  )}
                </div>
              ) : (
                <>
                  <p className="text-[12px] text-ink">{item.meaning ?? '—'}</p>
                  {item.translation && (
                    <p className="mt-1 text-[12px] text-muted">Translation: {item.translation}</p>
                  )}
                  {item.notes && <p className="mt-2 text-[11px] text-muted">{item.notes}</p>}
                  <Button variant="secondary" className="mt-3" onClick={startEditing}>
                    Edit
                  </Button>
                </>
              )}
            </div>

            <div className="border-b border-line py-5">
              <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
                Occurrences ({item.occurrences.length})
              </span>
              {item.occurrences.map((occurrence) => (
                <OccurrenceRow
                  key={occurrence.id}
                  occurrence={occurrence}
                  term={item.display_form}
                />
              ))}
            </div>

            <div className="py-5">
              <button
                type="button"
                className={dangerButtonClassName}
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete from vocabulary'}
              </button>
              {deleteMutation.isError && (
                <p className="mt-2 text-center text-[11px] text-danger" role="alert">
                  Couldn't delete this word.
                </p>
              )}
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
