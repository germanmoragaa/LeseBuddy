import { Card } from '../../components/Card'
import { Badge } from '../../components/Badge'
import { mockStudyActivity } from '../../mocks/progress'

export function StudyActivityChart() {
  const totalActivities = mockStudyActivity.reduce((sum, point) => sum + point.count, 0)
  const highlightIndex = mockStudyActivity.reduce(
    (best, point, index, all) => (point.heightPercent > all[best].heightPercent ? index : best),
    0,
  )

  return (
    <Card className="min-h-[350px] p-5.5 lg:col-span-1">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Study activity
          </span>
          <h2 className="mt-1.5 text-[17px]">A steady week</h2>
        </div>
        <Badge>{totalActivities} activities</Badge>
      </div>
      <div className="mt-5.5 grid h-[220px] grid-cols-[25px_1fr]">
        <div className="flex flex-col justify-between pb-5 text-[8px] text-[#aaaaaa]">
          <span>12</span>
          <span>8</span>
          <span>4</span>
          <span>0</span>
        </div>
        <div className="flex items-end justify-around border-b border-line">
          {mockStudyActivity.map((point, index) => (
            <div key={point.dayLabel + index} className="group relative flex h-full w-[8%] items-end justify-center">
              <span className="pointer-events-none absolute bottom-[calc(100%+4px)] hidden text-[8px] group-hover:block">
                {point.count}
              </span>
              <div
                className={`w-[18px] min-h-[10px] rounded-t-[5px] ${
                  index === highlightIndex ? 'bg-action' : 'bg-[#b9d9c3]'
                }`}
                style={{ height: `${point.heightPercent}%` }}
              />
              <small className="absolute -bottom-5 text-[8px]">{point.dayLabel}</small>
            </div>
          ))}
        </div>
      </div>
      <div className="ml-6 mt-8.5 flex justify-between text-[9px] text-muted">
        <span>
          <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-action" /> Reviews &amp;
          saved words
        </span>
        <span>May 15–21</span>
      </div>
    </Card>
  )
}
