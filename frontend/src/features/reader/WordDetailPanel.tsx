import { useQuery, useMutation } from '@tanstack/react-query'
import { Bookmark, BookmarkCheck, Languages, Loader2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

import { Button } from '../../components/Button'
import { ApiError, getDictionaryEntry, isApiErrorDetail, saveVocabularyItem, translateSelection } from '../../lib/api'
import type { CodePointIndex } from '../../lib/textOffsets'
import type { SeparableVerb, Token } from '../../types/analysis'
import { formatMorph, posLabel, resolveGender } from './grammarLabels'
import type { TokenSelectionRange } from './useTokenSelection'

interface WordDetailPanelProps {
  articleId: string
  originalText: string
  codePointIndex: CodePointIndex
  tokens: Token[]
  selection: TokenSelectionRange
  separableVerbs: SeparableVerb[]
  savedItemId: string | null
  translationDisabled: boolean
  onTranslationUnavailable: () => void
  onSaved: () => void
  onClose: () => void
}

// Error codes the translate endpoint can return where re-trying on every subsequent word
// click would just waste quota/log noise for the rest of this session — see
// docs/decisions/0004-translations-and-dictionary.md.
const TRANSLATION_DISABLING_CODES = new Set(['translation_not_configured', 'translation_quota_exceeded'])

export function WordDetailPanel({
  articleId,
  originalText,
  codePointIndex,
  tokens,
  selection,
  separableVerbs,
  savedItemId,
  translationDisabled,
  onTranslationUnavailable,
  onSaved,
  onClose,
}: WordDetailPanelProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const [sentenceTranslation, setSentenceTranslation] = useState<string | null>(null)
  const [savedItem, setSavedItem] = useState<{ id: string } | null>(
    savedItemId ? { id: savedItemId } : null,
  )

  // Move focus into the panel on open. Returning focus to the word that triggered it is the
  // caller's responsibility (Reader.tsx's onClose) — this component doesn't know which
  // element opened it.
  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  const { startTokenIndex, endTokenIndex } = selection
  const isSingleWord = startTokenIndex === endTokenIndex
  const start = tokens[startTokenIndex].start
  const end = tokens[endTokenIndex].end
  const surfaceText = codePointIndex.slice(originalText, start, end)

  const activeToken = tokens[startTokenIndex]
  const separableVerb = isSingleWord
    ? separableVerbs.find(
        (verb) =>
          verb.verb_token_index === startTokenIndex || verb.particle_token_index === startTokenIndex,
      )
    : undefined
  const morphLine = isSingleWord ? formatMorph(activeToken.morph, { excludeGender: true }) : null

  const dictionaryQuery = useQuery({
    queryKey: ['dictionary', articleId, start, end],
    queryFn: () => getDictionaryEntry(articleId, start, end),
  })

  const translationQuery = useQuery({
    queryKey: ['translation', articleId, start, end],
    queryFn: () => translateSelection(articleId, { start, end }),
    enabled: !translationDisabled,
    retry: false,
  })

  useEffect(() => {
    if (!translationQuery.isError) return
    const error = translationQuery.error
    if (error instanceof ApiError && isApiErrorDetail(error.detail) && TRANSLATION_DISABLING_CODES.has(error.detail.code)) {
      onTranslationUnavailable()
    }
  }, [translationQuery.isError, translationQuery.error, onTranslationUnavailable])

  const sentenceTranslationMutation = useMutation({
    mutationFn: () => translateSelection(articleId, { start, end, include_sentence: true }),
    onSuccess: (result) => setSentenceTranslation(result.sentence_translation),
  })

  const saveMutation = useMutation({
    mutationFn: () => saveVocabularyItem(articleId, start, end),
    onSuccess: (result) => {
      setSavedItem({ id: result.item.id })
      onSaved()
    },
  })

  const detectedGender = isSingleWord ? activeToken.morph.Gender : undefined
  const dictionaryGender = dictionaryQuery.data?.entry?.gender
  const resolvedGender = isSingleWord ? resolveGender(detectedGender, dictionaryGender) : null

  const translationErrorMessage =
    translationQuery.isError &&
    translationQuery.error instanceof ApiError &&
    isApiErrorDetail(translationQuery.error.detail)
      ? translationQuery.error.detail.message
      : "Couldn't load a translation right now."

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close word detail"
        onClick={onClose}
        className="absolute inset-0 w-full border-0 bg-black/30"
      />
      <aside
        role="dialog"
        aria-label="Word detail"
        className="fixed inset-x-0 bottom-0 z-50 max-h-[70vh] overflow-y-auto rounded-t-2xl border-t border-line bg-white p-6 shadow-[0_-20px_60px_rgb(25_40_31_/_0.14)] sm:inset-y-0 sm:right-0 sm:left-auto sm:bottom-auto sm:max-h-none sm:w-full sm:max-w-[400px] sm:rounded-t-none sm:border-t-0 sm:border-l sm:shadow-[-20px_0_60px_rgb(25_40_31_/_0.14)]"
      >
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Word detail
          </span>
          <Button ref={closeButtonRef} variant="icon" aria-label="Close word detail" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="border-b border-line py-7">
          <h2 className="mb-1 mt-2.5 text-[28px] tracking-tight">{surfaceText}</h2>

          {isSingleWord ? (
            <>
              <p className="text-muted">
                Lemma: <span className="text-ink">{separableVerb?.lemma ?? activeToken.lemma}</span>
              </p>
              <p className="mt-1 text-muted">
                {separableVerb ? 'Verb (separable)' : posLabel(activeToken.pos)}
              </p>
              {resolvedGender && (
                <p className="mt-1 text-muted">
                  Gender: <span className="text-ink">{resolvedGender.label}</span>{' '}
                  <span className="text-[10px] uppercase tracking-wide text-muted">
                    ({resolvedGender.source === 'dictionary' ? 'Dictionary' : 'Detected'})
                  </span>
                </p>
              )}
              {morphLine && <p className="mt-1 text-muted">{morphLine}</p>}
              {separableVerb && (
                <p className="mt-3 rounded-sm bg-surface-mint px-3 py-2 text-[11px] text-brand">
                  Separable verb: both highlighted parts combine into{' '}
                  <strong>{separableVerb.lemma}</strong>.
                </p>
              )}
            </>
          ) : (
            <p className="text-muted">
              Expression · offsets {start}–{end}
            </p>
          )}
        </div>

        <div className="border-b border-line py-5">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Dictionary
          </span>
          {dictionaryQuery.isPending && (
            <p className="mt-2 flex items-center gap-2 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" aria-hidden="true" /> Looking up…
            </p>
          )}
          {dictionaryQuery.isError && (
            <p className="mt-2 text-sm text-danger" role="alert">
              Couldn't load dictionary data.
            </p>
          )}
          {dictionaryQuery.data && dictionaryQuery.data.entry === null && (
            <p className="mt-2 text-sm text-muted">No dictionary entry found for this word.</p>
          )}
          {dictionaryQuery.data?.entry && (
            <div className="mt-2">
              {dictionaryQuery.data.entry.plural && (
                <p className="text-sm text-muted">
                  Plural: <span className="text-ink">{dictionaryQuery.data.entry.plural}</span>
                </p>
              )}
              <ul className="mt-1 list-disc pl-4 text-sm text-ink">
                {dictionaryQuery.data.entry.glosses.map((gloss, index) => (
                  <li key={index}>{gloss}</li>
                ))}
              </ul>
              <p className="mt-2 text-[10px] text-muted">
                Dictionary data from Wiktionary, licensed CC BY-SA.
              </p>
            </div>
          )}
        </div>

        <div className="border-b border-line py-5">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Translation
          </span>
          {translationDisabled && !translationQuery.isFetched && (
            <p className="mt-2 text-sm text-muted">Translations are unavailable right now.</p>
          )}
          {translationQuery.isPending && !translationDisabled && (
            <p className="mt-2 flex items-center gap-2 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" aria-hidden="true" /> Translating…
            </p>
          )}
          {translationQuery.isError && <p className="mt-2 text-sm text-danger" role="alert">{translationErrorMessage}</p>}
          {translationQuery.data && (
            <>
              <p className="mt-2 text-sm text-ink">{translationQuery.data.selection_translation}</p>
              {translationQuery.data.quota_warning && (
                <p className="mt-1 text-[11px] text-danger">{translationQuery.data.quota_warning}</p>
              )}
              {sentenceTranslation ? (
                <p className="mt-3 rounded-sm bg-[#f7f6f2] px-3 py-2 text-[12px] text-muted">
                  {sentenceTranslation}
                </p>
              ) : (
                <Button
                  variant="secondary"
                  className="mt-3 w-full"
                  onClick={() => sentenceTranslationMutation.mutate()}
                  disabled={sentenceTranslationMutation.isPending}
                >
                  <Languages size={16} aria-hidden="true" />
                  {sentenceTranslationMutation.isPending ? 'Translating sentence…' : 'Translate sentence'}
                </Button>
              )}
              {sentenceTranslationMutation.isError && (
                <p className="mt-1 text-[11px] text-danger" role="alert">
                  Couldn't translate the sentence.
                </p>
              )}
            </>
          )}
        </div>

        <div className="py-5">
          {savedItem ? (
            <>
              <Button className="w-full" disabled>
                <BookmarkCheck size={16} aria-hidden="true" /> Saved
              </Button>
              <Link
                to={`/app/vocabulary?item=${savedItem.id}`}
                className="mt-2 block text-center text-[11px] text-action underline"
              >
                View in vocabulary
              </Link>
            </>
          ) : (
            <>
              <Button
                className="w-full"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                <Bookmark size={16} aria-hidden="true" />
                {saveMutation.isPending ? 'Saving…' : 'Save to vocabulary'}
              </Button>
              {saveMutation.isError && (
                <p className="mt-2 text-center text-[11px] text-danger" role="alert">
                  Couldn't save this word. Please try again.
                </p>
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
