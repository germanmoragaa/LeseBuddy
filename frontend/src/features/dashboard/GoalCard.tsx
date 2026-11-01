import { Sparkles } from 'lucide-react'

import { ProgressBar } from '../../components/ProgressBar'
import { mockGoalProgress } from '../../mocks/dashboard'

export function GoalCard() {
  const percent = Math.round((mockGoalProgress.minutesToday / mockGoalProgress.minutesGoal) * 100)

  return (
    <section className="rounded-md border border-[#d4e8d8] bg-surface-mint p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your daily goal
          </span>
          <h3 className="mt-1.5 text-[15px] leading-snug">A little every day adds up.</h3>
        </div>
        <span className="grid h-9 w-9 rotate-6 place-items-center rounded-sm bg-accent text-[#816a16]">
          <Sparkles size={20} aria-hidden="true" />
        </span>
      </div>
      <div className="my-4 flex items-baseline">
        <strong className="text-[27px]">{mockGoalProgress.minutesToday}</strong>
        <span className="text-[11px] text-muted">/ {mockGoalProgress.minutesGoal} minutes</span>
        <small className="ml-auto text-[10px] font-bold">{percent}%</small>
      </div>
      <ProgressBar value={percent} tone="accent" />
    </section>
  )
}
