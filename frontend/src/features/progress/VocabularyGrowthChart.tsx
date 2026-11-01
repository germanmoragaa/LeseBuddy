import { Card } from '../../components/Card'
import { mockProgressOverview } from '../../mocks/progress'

export function VocabularyGrowthChart() {
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
          +{mockProgressOverview.vocabularyGrowthDelta}
        </strong>
      </div>
      <svg
        className="mt-4 h-[170px] w-full overflow-visible"
        viewBox="0 0 600 190"
        preserveAspectRatio="none"
        aria-label="Vocabulary growth over time"
      >
        <path
          d="M0 165C80 151 90 132 160 130S235 93 300 105s86-52 145-42 90-42 155-44V190H0Z"
          fill="rgb(79 143 105 / 0.08)"
        />
        <path
          d="M0 165C80 151 90 132 160 130S235 93 300 105s86-52 145-42 90-42 155-44"
          fill="none"
          stroke="var(--color-action)"
          strokeWidth={3}
          vectorEffect="non-scaling-stroke"
        />
        <circle cx={445} cy={63} r={5} fill="white" stroke="var(--color-action)" strokeWidth={3} />
      </svg>
      <div className="flex justify-between text-[8px] text-muted">
        <span>May 1</span>
        <span>May 8</span>
        <span>May 15</span>
        <span>Today</span>
      </div>
    </Card>
  )
}
