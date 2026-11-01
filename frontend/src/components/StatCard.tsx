import type { LucideIcon } from 'lucide-react'
import { ArrowRight } from 'lucide-react'

type StatTone = 'mint' | 'lavender' | 'yellow' | 'coral'

const toneClasses: Record<StatTone, string> = {
  mint: 'bg-surface-mint',
  lavender: 'bg-surface-lavender',
  yellow: 'bg-accent-soft',
  coral: 'bg-surface-coral',
}

interface StatCardProps {
  label: string
  value: string
  detail: string
  icon: LucideIcon
  tone?: StatTone
  positive?: boolean
  action?: { label: string; onClick: () => void }
}

export function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = 'mint',
  positive = false,
  action,
}: StatCardProps) {
  return (
    <article className="relative grid min-h-[142px] grid-cols-[1fr_auto] content-center rounded-md border border-line bg-white p-5">
      <span className="text-[11px] font-semibold text-muted">{label}</span>
      <div
        className={`col-start-2 row-span-2 row-start-1 grid h-[34px] w-[34px] place-items-center rounded-sm text-brand ${toneClasses[tone]}`}
        aria-hidden="true"
      >
        <Icon size={18} />
      </div>
      <strong className="col-start-1 mt-1 text-[28px] leading-none tracking-tight">{value}</strong>
      <small className={`col-start-1 mt-2 text-[10px] ${positive ? 'text-action' : 'text-muted'}`}>
        {detail}
      </small>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="absolute bottom-[18px] right-[18px] inline-flex items-center gap-1 text-[11px] font-bold text-action"
        >
          {action.label} <ArrowRight size={14} aria-hidden="true" />
        </button>
      )}
    </article>
  )
}
