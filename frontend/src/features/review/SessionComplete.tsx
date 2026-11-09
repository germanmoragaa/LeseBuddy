import { Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import type { ReviewRating } from '../../types/flashcards'
import { formatNextDue } from './reviewFormatting'

const ratingLabels: { id: ReviewRating; label: string; dotClass: string }[] = [
  { id: 'again', label: 'Again', dotClass: 'bg-surface-coral' },
  { id: 'hard', label: 'Hard', dotClass: 'bg-accent' },
  { id: 'good', label: 'Good', dotClass: 'bg-action' },
  { id: 'easy', label: 'Easy', dotClass: 'bg-[#8d7db6]' },
]

interface SessionCompleteProps {
  cardsReviewed: number
  ratingCounts: Record<ReviewRating, number>
  nextDueAt: string | null
  onReviewAnother: () => void
}

export function SessionComplete({
  cardsReviewed,
  ratingCounts,
  nextDueAt,
  onReviewAnother,
}: SessionCompleteProps) {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen flex-col items-center bg-surface px-6 pt-20 text-center">
      <div className="relative grid h-[100px] w-[100px] place-items-center rounded-full bg-accent-soft text-brand">
        <Sparkles size={46} aria-hidden="true" />
      </div>
      <span className="mt-8 block text-[11px] font-bold uppercase tracking-wide text-muted">
        Practice complete
      </span>
      <h1 className="my-2 text-[36px] tracking-tight">Session complete!</h1>
      <p className="m-0 text-muted">You showed up for your German today. That counts.</p>

      <div className="my-8 rounded-md border border-line bg-white p-5">
        <strong className="block text-2xl">{cardsReviewed}</strong>
        <span className="mt-1 block text-[9px] text-muted">Cards reviewed</span>
      </div>

      <div className="mb-6 flex items-center gap-2 text-[9px] text-muted">
        {ratingLabels.map((rating) => (
          <span key={rating.id} className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${rating.dotClass}`} />
            {rating.label} <b className="text-ink">{ratingCounts[rating.id]}</b>
          </span>
        ))}
      </div>

      <p className="m-0 mb-6 text-[11px] text-muted">{formatNextDue(nextDueAt)}</p>

      <div className="flex gap-2.5">
        <Button onClick={() => navigate('/app')}>Back to dashboard</Button>
        <Button variant="secondary" onClick={onReviewAnother}>
          Check for more cards
        </Button>
      </div>
    </div>
  )
}
