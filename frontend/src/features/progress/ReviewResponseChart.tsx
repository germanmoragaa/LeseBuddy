import { Card } from '../../components/Card'
import type { RatingCounts, RatingPercentages } from '../../types/analytics'

interface ReviewResponseChartProps {
  ratingCounts: RatingCounts
  ratingPercentages: RatingPercentages
  retentionPercent: number | null
}

const segments: { key: keyof RatingCounts; label: string; barClass: string; dotClass: string }[] = [
  { key: 'again', label: 'Again', barClass: 'bg-surface-coral', dotClass: 'bg-surface-coral' },
  { key: 'hard', label: 'Hard', barClass: 'bg-accent', dotClass: 'bg-accent' },
  { key: 'good', label: 'Good', barClass: 'bg-action', dotClass: 'bg-action' },
  { key: 'easy', label: 'Easy', barClass: 'bg-[#8d7db6]', dotClass: 'bg-[#8d7db6]' },
]

export function ReviewResponseChart({
  ratingCounts,
  ratingPercentages,
  retentionPercent,
}: ReviewResponseChartProps) {
  const totalReviews = Object.values(ratingCounts).reduce((sum, count) => sum + count, 0)

  return (
    <Card className="p-5.5">
      <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
        Review responses
      </span>
      <h2 className="mt-1.5 text-[17px]">How reviews felt</h2>

      {totalReviews === 0 ? (
        <p className="mt-4 text-xs text-muted">No reviews in this range yet.</p>
      ) : (
        <>
          <p className="mt-1 text-[10px] text-muted">
            Your self-reported responses from {totalReviews} review
            {totalReviews === 1 ? '' : 's'}
            {retentionPercent !== null && ` · ${Math.round(retentionPercent)}% retention`}
          </p>
          <div className="my-5 flex h-3.5 gap-0.5 overflow-hidden rounded-full">
            {segments.map((segment) => (
              <span
                key={segment.key}
                className={`block ${segment.barClass}`}
                style={{ width: `${ratingPercentages[segment.key]}%` }}
              />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {segments.map((segment) => (
              <span key={segment.key} className="flex items-center gap-1.5 text-[9px] text-muted">
                <i className={`inline-block h-1.5 w-1.5 rounded-full ${segment.dotClass}`} />
                {segment.label}
                <b className="ml-auto text-ink">{Math.round(ratingPercentages[segment.key])}%</b>
              </span>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}
