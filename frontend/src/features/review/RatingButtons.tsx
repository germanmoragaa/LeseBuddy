import type { ReviewRating } from '../../types/flashcards'
import { mockRatingIntervals } from '../../mocks/flashcards'

const ratings: { id: ReviewRating; label: string; hoverBorder: string }[] = [
  { id: 'again', label: 'Again', hoverBorder: 'hover:border-danger' },
  { id: 'hard', label: 'Hard', hoverBorder: 'hover:border-[#c59235]' },
  { id: 'good', label: 'Good', hoverBorder: 'hover:border-action' },
  { id: 'easy', label: 'Easy', hoverBorder: 'hover:border-[#675796]' },
]

interface RatingButtonsProps {
  onRate: (rating: ReviewRating) => void
}

export function RatingButtons({ onRate }: RatingButtonsProps) {
  return (
    <div className="mx-auto mt-5.5 max-w-[620px] text-center">
      <span className="text-[10px] text-muted">How well did you remember?</span>
      <div className="mt-2.5 grid grid-cols-4 gap-2">
        {ratings.map((rating) => (
          <button
            key={rating.id}
            type="button"
            onClick={() => onRate(rating.id)}
            className={`grid min-h-[57px] place-items-center content-center rounded-sm border border-line bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action ${rating.hoverBorder}`}
          >
            <strong className="text-[11px]">{rating.label}</strong>
            <small className="mt-1 text-[8px] text-muted">{mockRatingIntervals[rating.id]}</small>
          </button>
        ))}
      </div>
    </div>
  )
}
