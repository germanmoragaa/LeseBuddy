import { Sparkles, Volume2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { ProgressBar } from '../../components/ProgressBar'
import { genderArticle, posLabel } from '../reader/grammarLabels'
import type { DueFlashcard, DueFlashcardsResponse, ReviewRating } from '../../types/flashcards'
import { RatingButtons } from './RatingButtons'
import { formatNextDue } from './reviewFormatting'
import { SessionComplete } from './SessionComplete'
import { useDueCards } from './useDueCards'
import { useReviewSummary } from './useReviewSummary'
import { useSubmitReview } from './useSubmitReview'

const QUEUE_LIMIT = 20
const EMPTY_RATING_COUNTS: Record<ReviewRating, number> = { again: 0, hard: 0, good: 0, easy: 0 }

// Occurrence offsets aren't carried on the flashcard payload, so a case-insensitive substring
// match against the display form is the same reasonable approximation
// VocabularyDetailDrawer.tsx uses for highlighting a word within its saved context sentence.
function highlightSentence(sentence: string, term: string): ReactNode {
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

function CenteredMessage({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f4f2ec] text-sm text-muted">
      {children}
    </div>
  )
}

function EmptyDueState({ nextDueAt }: { nextDueAt: string | null }) {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#f4f2ec] px-6 text-center">
      <div className="grid h-[100px] w-[100px] place-items-center rounded-full bg-surface-mint text-brand">
        <Sparkles size={46} aria-hidden="true" />
      </div>
      <h1 className="text-[28px] tracking-tight">You're all caught up!</h1>
      <p className="m-0 max-w-[420px] text-muted">{formatNextDue(nextDueAt)}</p>
      <div className="mt-4 flex gap-2.5">
        <Button onClick={() => navigate('/app/reader')}>Read something new</Button>
        <Button variant="secondary" onClick={() => navigate('/app/vocabulary')}>
          Browse your vocabulary
        </Button>
      </div>
    </div>
  )
}

export function Flashcards() {
  const navigate = useNavigate()
  const dueQuery = useDueCards(QUEUE_LIMIT)
  const summaryQuery = useReviewSummary()
  const submitMutation = useSubmitReview()

  const [queue, setQueue] = useState<DueFlashcard[] | null>(null)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [clientReviewId, setClientReviewId] = useState<string | null>(null)
  const [pendingRating, setPendingRating] = useState<ReviewRating | null>(null)
  const [sessionPhase, setSessionPhase] = useState<'reviewing' | 'finishing' | 'complete'>(
    'reviewing',
  )
  const [sessionStats, setSessionStats] = useState({
    cardsReviewed: 0,
    ratingCounts: { ...EMPTY_RATING_COUNTS },
  })

  // Seed the queue once as a fixed snapshot to step through — later invalidations (e.g. from
  // reviewing a card) must not reshuffle the cards still ahead in this session. Derived during
  // render (React's documented pattern for "adjust state once when an external value first
  // arrives") rather than in an effect, since dueQuery.data itself already comes from an
  // effect inside TanStack Query — this only needs to react to it, not re-synchronize.
  const [seenInitialData, setSeenInitialData] = useState<DueFlashcardsResponse | undefined>(
    undefined,
  )
  if (queue === null && dueQuery.data && dueQuery.data !== seenInitialData) {
    setSeenInitialData(dueQuery.data)
    setQueue(dueQuery.data.items)
    setIndex(0)
  }

  function ensureClientReviewId(): string {
    if (clientReviewId) return clientReviewId
    const id = crypto.randomUUID()
    setClientReviewId(id)
    return id
  }

  async function finishBatchOrContinue() {
    setSessionPhase('finishing')
    const [dueResult] = await Promise.all([dueQuery.refetch(), summaryQuery.refetch()])
    const freshItems = dueResult.data?.items ?? []
    if (freshItems.length > 0) {
      setQueue(freshItems)
      setIndex(0)
      setRevealed(false)
      setSessionPhase('reviewing')
    } else {
      setSessionPhase('complete')
    }
  }

  function handleRatingSuccess(rating: ReviewRating) {
    setSessionStats((previous) => ({
      cardsReviewed: previous.cardsReviewed + 1,
      ratingCounts: {
        ...previous.ratingCounts,
        [rating]: previous.ratingCounts[rating] + 1,
      },
    }))
    setClientReviewId(null)
    setPendingRating(null)
    setRevealed(false)

    if (queue && index + 1 < queue.length) {
      setIndex(index + 1)
    } else {
      void finishBatchOrContinue()
    }
  }

  function submitRating(card: DueFlashcard, rating: ReviewRating) {
    if (submitMutation.isPending) return
    const id = ensureClientReviewId()
    setPendingRating(rating)
    submitMutation.mutate(
      { flashcard_id: card.id, rating, client_review_id: id },
      { onSuccess: () => handleRatingSuccess(rating) },
    )
  }

  const currentCard = queue && queue.length > 0 ? queue[index] : null

  function retry() {
    if (currentCard && pendingRating) submitRating(currentCard, pendingRating)
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (sessionPhase !== 'reviewing' || !currentCard) return
      if (event.code === 'Space' && !revealed) {
        event.preventDefault()
        setRevealed(true)
        return
      }
      if (!revealed || submitMutation.isPending) return
      const ratingByKey: Record<string, ReviewRating> = {
        '1': 'again',
        '2': 'hard',
        '3': 'good',
        '4': 'easy',
      }
      const rating = ratingByKey[event.key]
      if (rating) {
        event.preventDefault()
        submitRating(currentCard, rating)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  if (dueQuery.isPending && queue === null) {
    return <CenteredMessage>Loading your review queue…</CenteredMessage>
  }

  if (dueQuery.isError && queue === null) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#f4f2ec] text-sm text-muted">
        <p role="alert">Couldn't load your review queue.</p>
        <Button variant="secondary" onClick={() => dueQuery.refetch()}>
          Try again
        </Button>
      </div>
    )
  }

  if (queue !== null && queue.length === 0 && sessionStats.cardsReviewed === 0) {
    return <EmptyDueState nextDueAt={summaryQuery.data?.next_due_at ?? null} />
  }

  if (sessionPhase === 'complete') {
    return (
      <SessionComplete
        cardsReviewed={sessionStats.cardsReviewed}
        ratingCounts={sessionStats.ratingCounts}
        nextDueAt={summaryQuery.data?.next_due_at ?? null}
        onReviewAnother={() => {
          setSessionStats({ cardsReviewed: 0, ratingCounts: { ...EMPTY_RATING_COUNTS } })
          setQueue(null)
          setSessionPhase('reviewing')
          dueQuery.refetch()
        }}
      />
    )
  }

  if (sessionPhase === 'finishing' || !currentCard) {
    return <CenteredMessage>Checking for more cards…</CenteredMessage>
  }

  const { front, back } = currentCard
  const article = genderArticle(front.gender)

  return (
    <div className="min-h-screen bg-[#f4f2ec] px-6 py-10">
      <div className="mx-auto mb-4.5 flex max-w-[980px] items-start justify-between">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Daily review
          </span>
          <h1 className="my-1.5 text-[26px] tracking-tight">Time for a little practice</h1>
          <p className="m-0 text-[11px] text-muted">
            A few minutes today can make tomorrow's reading easier.
          </p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/app')}>
          Exit session
        </Button>
      </div>

      <div className="mx-auto mb-8 grid max-w-[980px] grid-cols-[140px_1fr] items-center gap-3.5 text-[10px] text-muted">
        <span>
          <strong className="text-ink">
            {index + 1} of {queue!.length}
          </strong>{' '}
          cards
        </span>
        <ProgressBar value={((index + 1) / queue!.length) * 100} />
      </div>

      <div
        className={`relative mx-auto flex max-w-[620px] flex-col rounded-lg border border-line bg-white px-6 pb-9 pt-7 shadow-[0_18px_55px_rgb(43_56_45_/_0.08)] sm:px-11 ${
          revealed ? 'min-h-[520px]' : 'min-h-[460px]'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-extrabold uppercase tracking-wide text-action">
            German
          </span>
          <Button
            variant="icon"
            aria-label={`Listen to pronunciation of ${front.display_form}`}
          >
            <Volume2 size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <h2 className="text-[34px] tracking-tight">
            {article && <span className="text-muted">{article} </span>}
            {front.display_form}
          </h2>
          <span className="mt-1.5 text-[11px] italic text-muted">
            {posLabel(front.part_of_speech)}
          </span>

          {!revealed ? (
            <small className="mt-9 text-[9px] text-muted">
              Think of the meaning before revealing the answer.
            </small>
          ) : (
            <div className="mt-9 w-full animate-[fade_0.2s_ease] border-t border-line pt-6">
              <span className="text-[9px] uppercase tracking-wide text-muted">
                English meaning
              </span>
              <h3 className="my-1.5 text-[23px] text-brand">
                {back.translation ?? back.glosses[0] ?? '—'}
              </h3>
              {back.glosses.length > 0 && (
                <p className="m-0 text-[11px] text-muted">{back.glosses.join('; ')}</p>
              )}
              {back.context_sentence && (
                <p className="my-4.5 rounded-sm bg-[#f7f6f2] px-4 py-3.5 font-serif text-base">
                  {highlightSentence(back.context_sentence, front.display_form)}
                </p>
              )}
            </div>
          )}

          <div aria-live="polite" className="sr-only">
            {revealed ? `Answer revealed: ${back.translation ?? back.glosses[0] ?? ''}` : ''}
          </div>
        </div>

        {!revealed && (
          <Button className="w-full" onClick={() => setRevealed(true)}>
            Reveal answer
          </Button>
        )}

        {submitMutation.isError && (
          <div className="mt-4 flex flex-col items-center gap-2 text-center">
            <p role="alert" className="text-[11px] text-danger">
              Couldn't save that review.
            </p>
            <Button variant="secondary" onClick={retry}>
              Try again
            </Button>
          </div>
        )}
      </div>

      {revealed && (
        <RatingButtons
          preview={currentCard.preview}
          disabled={submitMutation.isPending}
          onRate={(rating) => submitRating(currentCard, rating)}
        />
      )}

      <div className="mt-6 text-center text-[8px] text-[#aaaaaa]">
        Press <kbd className="rounded-[4px] border border-line bg-white px-1 py-0.5">Space</kbd>{' '}
        to reveal · Use{' '}
        <kbd className="rounded-[4px] border border-line bg-white px-1 py-0.5">1–4</kbd> to rate
      </div>
    </div>
  )
}
