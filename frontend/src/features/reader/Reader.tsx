import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Home as HomeIcon, Pencil, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Button } from '../../components/Button'
import {
  getArticle,
  getArticleAnalysis,
  getVocabularyOccurrences,
  updateArticle,
} from '../../lib/api'
import { CodePointIndex } from '../../lib/textOffsets'
import type { Token } from '../../types/analysis'
import type { VocabularyOccurrenceSummary } from '../../types/vocabulary'
import { ArticleText } from './ArticleText'
import { useDeleteArticle } from './useDeleteArticle'
import { useTokenSelection } from './useTokenSelection'
import { WordDetailPanel } from './WordDetailPanel'

// Stable references so useMemo dependents below don't re-run every render just because
// `data` is still undefined (a fresh `?? []` literal would be a new array each time).
const EMPTY_TOKENS: Token[] = []
const EMPTY_OCCURRENCES: VocabularyOccurrenceSummary[] = []

export function Reader() {
  const { articleId } = useParams<{ articleId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const wordRefs = useRef<Record<number, HTMLButtonElement | null>>({})

  const articleQuery = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => getArticle(articleId!),
    enabled: !!articleId,
  })

  const analysisQuery = useQuery({
    queryKey: ['article-analysis', articleId],
    queryFn: () => getArticleAnalysis(articleId!),
    enabled: !!articleId && articleQuery.isSuccess,
  })

  const vocabularyOccurrencesQuery = useQuery({
    queryKey: ['article-vocabulary-occurrences', articleId],
    queryFn: () => getVocabularyOccurrences(articleId!),
    enabled: !!articleId && articleQuery.isSuccess,
  })

  const [isRenaming, setIsRenaming] = useState(false)
  const [titleInput, setTitleInput] = useState('')

  const renameMutation = useMutation({
    mutationFn: (title: string) => updateArticle(articleId!, { title }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      queryClient.setQueryData(['article', articleId], updated)
      setIsRenaming(false)
    },
  })

  const deleteMutation = useDeleteArticle(articleId!)

  // Lifted above the word-detail panel (which remounts on every new selection) so that once
  // translations are unavailable (not configured / quota exhausted), the app stops
  // re-attempting them on every subsequent word click for the rest of this session.
  const [translationDisabled, setTranslationDisabled] = useState(false)

  const tokens = analysisQuery.data?.tokens ?? EMPTY_TOKENS
  const {
    wordTokenIndices,
    activeTokenIndex,
    selection,
    announcement,
    handleWordClick,
    handleWordMouseDown,
    handleWordMouseEnter,
    endDrag,
    handleKeyDown,
    clearSelection,
  } = useTokenSelection(tokens)

  useEffect(() => {
    window.addEventListener('mouseup', endDrag)
    return () => window.removeEventListener('mouseup', endDrag)
  }, [endDrag])

  // Move browser focus to match the roving-tabindex cursor, but only while focus is already
  // inside the reading area — otherwise this would steal focus on every render, including
  // the initial page load.
  useEffect(() => {
    const isFocusInsideReader = Object.values(wordRefs.current).includes(
      document.activeElement as HTMLButtonElement | null,
    )
    if (isFocusInsideReader) {
      wordRefs.current[activeTokenIndex]?.focus()
    }
  }, [activeTokenIndex])

  const codePointIndex = useMemo(
    () => (articleQuery.data ? new CodePointIndex(articleQuery.data.original_text) : null),
    [articleQuery.data],
  )

  const occurrences = vocabularyOccurrencesQuery.data ?? EMPTY_OCCURRENCES

  // A token is "saved" if it falls within some occurrence's span — occurrence offsets always
  // land on real token boundaries (the backend derives them the same way), so this never
  // partially-highlights a word.
  const savedTokenIndices = useMemo(() => {
    const indices = new Set<number>()
    for (const occurrence of occurrences) {
      tokens.forEach((token, index) => {
        if (token.start >= occurrence.start_offset && token.end <= occurrence.end_offset) {
          indices.add(index)
        }
      })
    }
    return indices
  }, [occurrences, tokens])

  const savedItemId = useMemo(() => {
    if (!selection) return null
    const start = tokens[selection.startTokenIndex].start
    const end = tokens[selection.endTokenIndex].end
    const match = occurrences.find(
      (occurrence) => occurrence.start_offset === start && occurrence.end_offset === end,
    )
    return match?.vocabulary_item_id ?? null
  }, [selection, tokens, occurrences])

  function closePanel() {
    const returnFocusIndex = activeTokenIndex
    clearSelection()
    wordRefs.current[returnFocusIndex]?.focus()
  }

  function startRenaming() {
    setTitleInput(articleQuery.data?.title ?? '')
    setIsRenaming(true)
  }

  function handleDelete() {
    if (window.confirm('Delete this text from your library? This cannot be undone.')) {
      deleteMutation.mutate(undefined, { onSuccess: () => navigate('/app/reader') })
    }
  }

  const article = articleQuery.data
  const titleText = article?.title ?? (articleQuery.isPending ? 'Loading…' : 'Untitled')

  return (
    <div className="min-h-screen bg-[#f3f2ee]">
      <header className="sticky top-0 z-20 flex min-h-[64px] flex-wrap items-center gap-3 border-b border-line bg-white px-6 py-3">
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate('/app/reader')}>
            <ArrowLeft size={16} aria-hidden="true" /> Back to library
          </Button>
          <Button variant="ghost" onClick={() => navigate('/app')}>
            <HomeIcon size={16} aria-hidden="true" /> Home
          </Button>
        </div>

        <div className="min-w-0 flex-1">
          {isRenaming ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={titleInput}
                onChange={(event) => setTitleInput(event.target.value)}
                aria-label="Article title"
                autoFocus
                className="min-w-0 flex-1 rounded-sm border border-line px-2.5 py-1.5 text-[12px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
              />
              <Button
                variant="secondary"
                className="min-h-[34px] px-3 text-[11px]"
                onClick={() => renameMutation.mutate(titleInput.trim())}
                disabled={titleInput.trim().length === 0 || renameMutation.isPending}
              >
                {renameMutation.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button
                variant="ghost"
                className="min-h-[34px] px-3 text-[11px]"
                onClick={() => setIsRenaming(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <strong className="block truncate text-[13px]">{titleText}</strong>
          )}
          {renameMutation.isError && (
            <p className="mt-1 text-[10px] text-danger" role="alert">
              Couldn't rename this text.
            </p>
          )}
        </div>

        {article && !isRenaming && (
          <div className="flex items-center gap-1.5">
            <Button variant="icon" aria-label="Rename article" onClick={startRenaming}>
              <Pencil size={16} aria-hidden="true" />
            </Button>
            <Button
              variant="icon"
              aria-label="Delete article"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 size={16} aria-hidden="true" />
            </Button>
          </div>
        )}
      </header>

      {deleteMutation.isError && (
        <p className="px-6 pt-4 text-center text-[11px] text-danger" role="alert">
          Couldn't delete this text.
        </p>
      )}

      {articleQuery.isPending && (
        <div className="flex min-h-[60vh] items-center justify-center text-sm text-muted">
          Loading article…
        </div>
      )}

      {articleQuery.isError && (
        <div className="flex min-h-[60vh] items-center justify-center text-sm text-muted">
          Couldn't load this article.
        </div>
      )}

      {article && (
        <div className="grid justify-center gap-5 p-6 lg:grid-cols-[minmax(500px,810px)_344px]">
          <main className="rounded-[3px] border border-line bg-white px-6 py-10 shadow-[0_8px_40px_rgb(49_52_45_/_0.05)] sm:px-16 sm:py-16">
            <h1 className="my-3 max-w-[600px] text-[clamp(30px,3.4vw,44px)] leading-tight tracking-tight">
              {article.title ?? 'Untitled'}
            </h1>
            <div className="my-8 flex items-center gap-2 text-action">
              <span className="h-px flex-1 bg-line" />
            </div>

            {analysisQuery.isPending && (
              <p className="text-sm text-muted" role="status">
                Analyzing text…
              </p>
            )}
            {analysisQuery.isError && (
              <p className="text-sm text-danger" role="alert">
                Couldn't analyze this text. Please try again later.
              </p>
            )}
            {analysisQuery.data && codePointIndex && (
              <ArticleText
                originalText={article.original_text}
                codePointIndex={codePointIndex}
                tokens={tokens}
                separableVerbs={analysisQuery.data.separable_verbs}
                activeTokenIndex={activeTokenIndex}
                selection={selection}
                savedTokenIndices={savedTokenIndices}
                wordRefs={wordRefs}
                onWordClick={handleWordClick}
                onWordMouseDown={handleWordMouseDown}
                onWordMouseEnter={handleWordMouseEnter}
                onKeyDown={handleKeyDown}
              />
            )}

            <div aria-live="polite" className="sr-only">
              {announcement}
            </div>
            {wordTokenIndices.length === 0 && analysisQuery.data && (
              <p className="text-sm text-muted">This text has no selectable words.</p>
            )}
          </main>

          {selection && analysisQuery.data && codePointIndex && articleId && (
            <WordDetailPanel
              key={`${selection.startTokenIndex}-${selection.endTokenIndex}`}
              articleId={articleId}
              originalText={article.original_text}
              codePointIndex={codePointIndex}
              tokens={tokens}
              selection={selection}
              separableVerbs={analysisQuery.data.separable_verbs}
              savedItemId={savedItemId}
              translationDisabled={translationDisabled}
              onTranslationUnavailable={() => setTranslationDisabled(true)}
              onSaved={() => vocabularyOccurrencesQuery.refetch()}
              onClose={closePanel}
            />
          )}
        </div>
      )}
    </div>
  )
}
