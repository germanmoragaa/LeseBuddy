import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { useDueCards } from '../review/useDueCards'
import { useReviewSummary } from '../review/useReviewSummary'

const PREVIEW_COUNT = 3

export function PracticeCard() {
  const navigate = useNavigate()
  const dueQuery = useDueCards(PREVIEW_COUNT)
  const summaryQuery = useReviewSummary()
  const cards = dueQuery.data?.items ?? []
  const dueCount = summaryQuery.data?.due_count ?? 0

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Quick practice
          </span>
          <h3 className="mt-1.5 text-[15px] leading-snug">Words ready for a little practice</h3>
        </div>
        {dueCount > 0 && (
          <span className="whitespace-nowrap rounded-[6px] bg-accent-soft px-2 py-1 text-[9px] font-bold text-[#775f0f]">
            {dueCount} due
          </span>
        )}
      </div>
      <div className="my-3.5">
        {dueQuery.isPending && <p className="py-4 text-center text-xs text-muted">Loading…</p>}

        {dueQuery.data && cards.length === 0 && (
          <p className="py-4 text-center text-xs text-muted">
            Nothing due right now — nice work staying on top of it.
          </p>
        )}

        {cards.map((card, index) => (
          <button
            type="button"
            key={card.id}
            onClick={() => navigate('/app/flashcards')}
            className="grid w-full min-h-12 grid-cols-[27px_1fr_auto] items-center gap-2.5 border-b border-line py-2 text-left last:border-b-0"
          >
            <span className="text-[9px] text-[#adb0a9]">0{index + 1}</span>
            <span>
              <strong className="block text-[11px]">{card.front.display_form}</strong>
              <small className="mt-0.5 block text-[9px] text-muted">
                {card.back.translation ?? card.back.glosses[0] ?? '—'}
              </small>
            </span>
            <ArrowRight size={16} aria-hidden="true" className="text-muted" />
          </button>
        ))}
      </div>
      <Button
        variant="secondary"
        className="w-full"
        disabled={dueCount === 0}
        onClick={() => navigate('/app/flashcards')}
      >
        {dueCount === 0 ? 'Nothing to review' : `Review ${dueCount} cards`}
      </Button>
    </Card>
  )
}
