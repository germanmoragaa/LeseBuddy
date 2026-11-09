import type { ReviewRating } from '../../types/flashcards'

const ratings: { id: ReviewRating; label: string; hoverBorder: string }[] = [
  { id: 'again', label: 'Again', hoverBorder: 'hover:border-danger' },
  { id: 'hard', label: 'Hard', hoverBorder: 'hover:border-[#c59235]' },
  { id: 'good', label: 'Good', hoverBorder: 'hover:border-action' },
  { id: 'easy', label: 'Easy', hoverBorder: 'hover:border-[#675796]' },
]

// "again" always schedules a 10-minute delay (see backend/app/services/scheduler.py's
// AGAIN_DELAY) — its preview interval_days is always 0, which isn't a useful label on its own.
function formatIntervalLabel(rating: ReviewRating, days: number): string {
  if (rating === 'again') return '10 min'
  return days === 1 ? '1 day' : `${days} days`
}

interface RatingButtonsProps {
  preview: Record<ReviewRating, number>
  disabled?: boolean
  onRate: (rating: ReviewRating) => void
}

export function RatingButtons({ preview, disabled = false, onRate }: RatingButtonsProps) {
  return (
    <div className="mx-auto mt-5.5 max-w-[620px] text-center">
      <span className="text-[10px] text-muted">How well did you remember?</span>
      <div className="mt-2.5 grid grid-cols-4 gap-2">
        {ratings.map((rating, index) => (
          <button
            key={rating.id}
            type="button"
            onClick={() => onRate(rating.id)}
            disabled={disabled}
            className={`grid min-h-[57px] place-items-center content-center rounded-sm border border-line bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:pointer-events-none disabled:opacity-50 ${rating.hoverBorder}`}
          >
            <strong className="text-[11px]">
              {rating.label} <span className="text-muted">({index + 1})</span>
            </strong>
            <small className="mt-1 text-[8px] text-muted">
              {formatIntervalLabel(rating.id, preview[rating.id])}
            </small>
          </button>
        ))}
      </div>
    </div>
  )
}
