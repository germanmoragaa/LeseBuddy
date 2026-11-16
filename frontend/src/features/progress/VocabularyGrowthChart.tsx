import { Card } from '../../components/Card'
import type { DayActivity } from '../../types/analytics'

interface VocabularyGrowthChartProps {
  days: DayActivity[]
}

const VIEW_WIDTH = 600
const VIEW_HEIGHT = 190
const BOTTOM_PADDING = 20

function buildChart(
  days: DayActivity[],
): { line: string; area: string; lastPoint: { x: number; y: number } } | null {
  if (days.length < 2) return null

  const values = days.map((day) => day.cumulative_vocabulary)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1

  const points = days.map((day, index) => {
    const x = (index / (days.length - 1)) * VIEW_WIDTH
    const y =
      VIEW_HEIGHT -
      BOTTOM_PADDING -
      ((day.cumulative_vocabulary - min) / span) * (VIEW_HEIGHT - BOTTOM_PADDING)
    return [x, y] as const
  })

  const line = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x} ${y}`).join(' ')
  const area = `${line} L${VIEW_WIDTH} ${VIEW_HEIGHT} L0 ${VIEW_HEIGHT} Z`
  const [lastX, lastY] = points[points.length - 1]
  return { line, area, lastPoint: { x: lastX, y: lastY } }
}

export function VocabularyGrowthChart({ days }: VocabularyGrowthChartProps) {
  const first = days[0]
  const last = days[days.length - 1]
  const delta = first && last ? last.cumulative_vocabulary - first.cumulative_vocabulary : 0
  const chart = buildChart(days)

  return (
    <Card className="p-5.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Vocabulary growth
          </span>
          <h2 className="mt-1.5 text-[17px]">Your vocabulary is growing</h2>
        </div>
        <strong className="text-[19px] text-action">
          {delta >= 0 ? '+' : ''}
          {delta}
        </strong>
      </div>

      {!chart ? (
        <p className="mt-10 text-center text-xs text-muted">Not enough data yet.</p>
      ) : (
        <>
          <svg
            className="mt-4 h-[170px] w-full overflow-visible"
            viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
            preserveAspectRatio="none"
            aria-label="Vocabulary growth over time"
          >
            <path d={chart.area} fill="rgb(79 143 105 / 0.08)" />
            <path
              d={chart.line}
              fill="none"
              stroke="var(--color-action)"
              strokeWidth={3}
              vectorEffect="non-scaling-stroke"
            />
            <circle
              cx={chart.lastPoint.x}
              cy={chart.lastPoint.y}
              r={5}
              fill="white"
              stroke="var(--color-action)"
              strokeWidth={3}
            />
          </svg>
          <div className="flex justify-between text-[8px] text-muted">
            <span>
              {new Date(`${first.date}T00:00:00`).toLocaleDateString(undefined, {
                day: 'numeric',
                month: 'short',
              })}
            </span>
            <span>Today</span>
          </div>
        </>
      )}
    </Card>
  )
}
