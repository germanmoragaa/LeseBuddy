import { ArrowRight, Bookmark, Check, Clock, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { mockProgressOverview } from '../../mocks/progress'
import type { TimeRange } from '../../types/progress'
import { ReviewResponseChart } from './ReviewResponseChart'
import { StudyActivityChart } from './StudyActivityChart'
import { VocabularyGrowthChart } from './VocabularyGrowthChart'

const ranges: TimeRange[] = ['7 days', '30 days', 'All time']

const onBrandButton =
  'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-sm border border-white/15 bg-white/10 px-4 text-[13px] font-bold text-white transition hover:-translate-y-px hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white'

interface Metric {
  icon: LucideIcon
  value: string
  label: string
  detail: string
}

export function Progress() {
  const navigate = useNavigate()
  const [range, setRange] = useState<TimeRange>('7 days')
  const overview = mockProgressOverview

  const metrics: Metric[] = [
    {
      icon: Bookmark,
      value: String(overview.vocabularySaved),
      label: 'Vocabulary saved',
      detail: `+${overview.vocabularySavedDeltaThisWeek} this week`,
    },
    {
      icon: Check,
      value: String(overview.reviewsCompleted),
      label: 'Reviews completed',
      detail: `+${overview.reviewsCompletedDeltaThisWeek} this week`,
    },
    {
      icon: Clock,
      value: `${overview.readingHours}h`,
      label: 'Reading time',
      detail: `+${overview.readingHoursDeltaThisWeek}h this week`,
    },
    {
      icon: Sparkles,
      value: `${overview.currentStreakDays} days`,
      label: 'Current streak',
      detail: `Personal best: ${overview.personalBestStreakDays}`,
    },
  ]

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
          {ranges.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setRange(item)}
              className={`min-h-[34px] rounded-sm px-3 text-[10px] font-bold ${
                range === item ? 'bg-white text-brand shadow-[0_2px_8px_rgb(33_46_36_/_0.06)]' : 'text-muted'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map((metric) => (
          <article key={metric.label} className="min-h-[132px] rounded-md border border-line bg-white p-5">
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

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_.8fr]">
        <StudyActivityChart />
        <section className="rounded-md border border-brand bg-brand p-5.5 text-white">
          <span className="grid h-10 w-10 place-items-center rounded-[12px] bg-accent text-[#7a6416]">
            <Sparkles size={20} aria-hidden="true" />
          </span>
          <span className="mt-7.5 block text-[11px] font-bold uppercase tracking-wide text-[#a9c8b7]">
            Your learning insight
          </span>
          <h2 className="max-w-[260px] text-2xl leading-tight">
            Expressions are your thing this week.
          </h2>
          <p className="text-[11px] leading-relaxed text-[#bed1c6]">
            You've saved more expressions than last week. Try reviewing a few of them in context.
          </p>
          <button
            type="button"
            className={`${onBrandButton} mt-4`}
            onClick={() => navigate('/flashcards')}
          >
            Review 8 waiting cards <ArrowRight size={16} aria-hidden="true" />
          </button>
        </section>
        <VocabularyGrowthChart />
        <ReviewResponseChart />
      </div>
    </div>
  )
}
