import { Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { ProgressBar } from '../../components/ProgressBar'
import { useAnalyticsOverview } from '../analytics/useAnalyticsOverview'

export function TodayCard() {
  const navigate = useNavigate()
  const { data: overview, isPending } = useAnalyticsOverview()

  const reviewsToday = overview?.reviews_today ?? 0
  const dueRemaining = overview?.due_now ?? 0
  const total = reviewsToday + dueRemaining
  const percent = total > 0 ? Math.round((reviewsToday / total) * 100) : 0

  return (
    <section className="rounded-md border border-[#d4e8d8] bg-surface-mint p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Today
          </span>
          <h3 className="mt-1.5 text-[15px] leading-snug">A little every day adds up.</h3>
        </div>
        <span className="grid h-9 w-9 rotate-6 place-items-center rounded-sm bg-accent text-[#816a16]">
          <Sparkles size={20} aria-hidden="true" />
        </span>
      </div>

      {isPending ? (
        <p className="my-4 text-xs text-muted">Loading…</p>
      ) : total === 0 ? (
        <p className="my-4 text-xs text-muted">
          Nothing due today — nice work staying on top of it.
        </p>
      ) : (
        <>
          <div className="my-4 flex items-baseline">
            <strong className="text-[27px]">{reviewsToday}</strong>
            <span className="text-[11px] text-muted">/ {total} reviews today</span>
            <small className="ml-auto text-[10px] font-bold">{percent}%</small>
          </div>
          <ProgressBar value={percent} tone="accent" />
          {dueRemaining > 0 && (
            <Button
              variant="secondary"
              className="mt-3 w-full"
              onClick={() => navigate('/app/flashcards')}
            >
              Review {dueRemaining} more
            </Button>
          )}
        </>
      )}
    </section>
  )
}
