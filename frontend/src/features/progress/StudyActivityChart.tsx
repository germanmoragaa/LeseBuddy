import { Badge } from '../../components/Badge'
import { Card } from '../../components/Card'
import type { AnalyticsRangeDays, DayActivity } from '../../types/analytics'

interface StudyActivityChartProps {
  days: DayActivity[]
  rangeDays: AnalyticsRangeDays
}

// For a 7-day range every bar gets a weekday label; for 30/90 that would overlap, so only
// every few bars get a short date label.
function labelStep(rangeDays: AnalyticsRangeDays): number {
  if (rangeDays === 7) return 1
  if (rangeDays === 30) return 5
  return 10
}

function formatLabel(dateIso: string, rangeDays: AnalyticsRangeDays): string {
  const date = new Date(`${dateIso}T00:00:00`)
  return rangeDays === 7
    ? date.toLocaleDateString(undefined, { weekday: 'short' }).slice(0, 1).toUpperCase()
    : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export function StudyActivityChart({ days, rangeDays }: StudyActivityChartProps) {
  const totalActivities = days.reduce((sum, point) => sum + point.reviews + point.words_saved, 0)
  const maxReviews = Math.max(1, ...days.map((point) => point.reviews))
  const highlightIndex = days.reduce(
    (best, point, index, all) => (point.reviews > all[best].reviews ? index : best),
    0,
  )
  const step = labelStep(rangeDays)
  const rangeLabel =
    days.length > 0
      ? `${new Date(`${days[0].date}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}–${new Date(`${days[days.length - 1].date}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}`
      : ''

  return (
    <Card className="min-h-[350px] p-5.5 lg:col-span-1">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Study activity
          </span>
          <h2 className="mt-1.5 text-[17px]">Reviews and words saved</h2>
        </div>
        <Badge>{totalActivities} activities</Badge>
      </div>

      {totalActivities === 0 ? (
        <p className="mt-10 text-center text-xs text-muted">
          No activity yet in this range — review some cards or save a word to see it here.
        </p>
      ) : (
        <>
          <div className="mt-5.5 grid h-[220px] grid-cols-[25px_1fr]">
            <div className="flex flex-col justify-between pb-5 text-[8px] text-[#aaaaaa]">
              <span>{maxReviews}</span>
              <span>{Math.round(maxReviews / 2)}</span>
              <span>0</span>
            </div>
            <div className="flex items-end justify-around border-b border-line">
              {days.map((point, index) => (
                <div
                  key={point.date}
                  className="group relative flex h-full w-full items-end justify-center"
                >
                  <span className="pointer-events-none absolute bottom-[calc(100%+4px)] hidden text-[8px] group-hover:block">
                    {point.reviews}
                  </span>
                  <div
                    className={`w-[60%] min-h-[2px] rounded-t-[5px] ${
                      index === highlightIndex ? 'bg-action' : 'bg-[#b9d9c3]'
                    }`}
                    style={{ height: `${(point.reviews / maxReviews) * 100}%` }}
                  />
                  {index % step === 0 && (
                    <small className="absolute -bottom-5 whitespace-nowrap text-[8px]">
                      {formatLabel(point.date, rangeDays)}
                    </small>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="ml-6 mt-8.5 flex justify-between text-[9px] text-muted">
            <span>
              <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-action" /> Reviews
              per day
            </span>
            <span>{rangeLabel}</span>
          </div>
        </>
      )}
    </Card>
  )
}
