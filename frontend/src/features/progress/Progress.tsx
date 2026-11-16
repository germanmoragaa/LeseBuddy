import { Bookmark, Check, Sparkles, Target } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'

import { useAnalyticsActivity } from '../analytics/useAnalyticsActivity'
import { useAnalyticsOverview } from '../analytics/useAnalyticsOverview'
import type { AnalyticsRangeDays } from '../../types/analytics'
import { ReviewResponseChart } from './ReviewResponseChart'
import { StudyActivityChart } from './StudyActivityChart'
import { VocabularyGrowthChart } from './VocabularyGrowthChart'

const RANGES: { label: string; days: AnalyticsRangeDays }[] = [
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
]

interface Metric {
  icon: LucideIcon
  value: string
  label: string
  detail: string
}

export function Progress() {
  const [range, setRange] = useState<AnalyticsRangeDays>(7)
  const overviewQuery = useAnalyticsOverview()
  const activityQuery = useAnalyticsActivity(range)

  const overview = overviewQuery.data
  const activity = activityQuery.data
  const days = activity?.days ?? []

  const wordsSavedInRange = days.reduce((sum, day) => sum + day.words_saved, 0)
  const reviewsInRange = days.reduce((sum, day) => sum + day.reviews, 0)
  const hasAnyActivity = reviewsInRange > 0 || wordsSavedInRange > 0 || (overview?.words_saved ?? 0) > 0

  const metrics: Metric[] = overview
    ? [
        {
          icon: Bookmark,
          value: String(wordsSavedInRange),
          label: 'Vocabulary saved',
          detail: `Last ${range} days`,
        },
        {
          icon: Check,
          value: String(reviewsInRange),
          label: 'Reviews completed',
          detail: `Last ${range} days`,
        },
        {
          icon: Target,
          value: activity?.retention_percent !== null && activity?.retention_percent !== undefined
            ? `${Math.round(activity.retention_percent)}%`
            : '—',
          label: 'Retention',
          detail: 'Non-"again" ratings',
        },
        {
          icon: Sparkles,
          value: `${overview.streak.current_days} days`,
          label: 'Current streak',
          detail: `Personal best: ${overview.streak.longest_days}`,
        },
      ]
    : []

  return (
    <div>
      <div className="mb-7 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Learning overview
          </span>
          <h1 className="my-1.5 text-[33px] tracking-tight">Your progress</h1>
          <p className="m-0 text-[13px] text-muted">Small steps, stronger German.</p>
        </div>
        <div className="flex gap-0.5 rounded-sm bg-[#efeee9] p-1">
          {RANGES.map((item) => (
            <button
              key={item.days}
              type="button"
              onClick={() => setRange(item.days)}
              className={`min-h-[34px] rounded-sm px-3 text-[10px] font-bold ${
                range === item.days
                  ? 'bg-white text-brand shadow-[0_2px_8px_rgb(33_46_36_/_0.06)]'
                  : 'text-muted'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {overviewQuery.isPending || activityQuery.isPending ? (
        <p className="py-14 text-center text-sm text-muted">Loading your progress…</p>
      ) : !hasAnyActivity ? (
        <div className="flex flex-col items-center gap-2 rounded-md border border-line bg-white px-5 py-14 text-center">
          <p className="text-sm text-muted">
            You haven't saved any words or done any reviews yet — your progress will show up
            here once you do.
          </p>
        </div>
      ) : (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {metrics.map((metric) => (
              <article
                key={metric.label}
                className="min-h-[132px] rounded-md border border-line bg-white p-5"
              >
                <div className="flex items-center justify-between">
                  <span className="grid h-[34px] w-[34px] place-items-center rounded-sm bg-surface-mint text-brand">
                    <metric.icon size={18} aria-hidden="true" />
                  </span>
                  <small className="text-[9px] text-action">{metric.detail}</small>
                </div>
                <strong className="mt-4 block text-[28px] leading-none tracking-tight">
                  {metric.value}
                </strong>
                <span className="mt-1.5 block text-[11px] text-muted">{metric.label}</span>
              </article>
            ))}
          </section>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <StudyActivityChart days={days} rangeDays={range} />
            <ReviewResponseChart
              ratingCounts={activity!.rating_counts}
              ratingPercentages={activity!.rating_percentages}
              retentionPercent={activity!.retention_percent}
            />
            <div className="lg:col-span-2">
              <VocabularyGrowthChart days={days} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
