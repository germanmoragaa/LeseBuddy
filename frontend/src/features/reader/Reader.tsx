import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Bookmark, MoreHorizontal } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Button } from '../../components/Button'
import { getArticle, getArticleAnalysis } from '../../lib/api'
import { CodePointIndex } from '../../lib/textOffsets'
import { ArticleText } from './ArticleText'
import { useTokenSelection } from './useTokenSelection'
import { WordDetailPanel } from './WordDetailPanel'

export function Reader() {
  const { articleId } = useParams<{ articleId: string }>()
  const navigate = useNavigate()
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

  const tokens = analysisQuery.data?.tokens ?? []
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

  function closePanel() {
    const returnFocusIndex = activeTokenIndex
    clearSelection()
    wordRefs.current[returnFocusIndex]?.focus()
  }

  if (articleQuery.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f3f2ee] text-sm text-muted">
        Loading article…
      </div>
    )
  }

  if (articleQuery.isError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#f3f2ee] text-sm text-muted">
        <p>Couldn't load this article.</p>
        <Button variant="secondary" onClick={() => navigate('/app')}>
          Back to dashboard
        </Button>
      </div>
    )
  }

  const article = articleQuery.data

  return (
    <div className="min-h-screen bg-[#f3f2ee]">
      <div className="grid min-h-[70px] grid-cols-[40px_minmax(0,1fr)_40px_40px] items-center gap-2.5 border-b border-line bg-white px-6">
        <Button variant="icon" aria-label="Back to dashboard" onClick={() => navigate('/app')}>
          <ArrowLeft size={18} aria-hidden="true" />
        </Button>
        <div className="min-w-0">
          <strong className="block truncate text-[13px]">{article.title ?? 'Untitled'}</strong>
        </div>
        <Button variant="icon" aria-label="Bookmark this article">
          <Bookmark size={18} aria-hidden="true" />
        </Button>
        <Button variant="icon" aria-label="More options">
          <MoreHorizontal size={18} aria-hidden="true" />
        </Button>
      </div>

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

        {selection && analysisQuery.data && codePointIndex && (
          <WordDetailPanel
            originalText={article.original_text}
            codePointIndex={codePointIndex}
            tokens={tokens}
            selection={selection}
            separableVerbs={analysisQuery.data.separable_verbs}
            onClose={closePanel}
          />
        )}
      </div>
    </div>
  )
}
