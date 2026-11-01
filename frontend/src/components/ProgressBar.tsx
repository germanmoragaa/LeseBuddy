interface ProgressBarProps {
  value: number
  tone?: 'action' | 'accent'
  className?: string
}

const fillTone: Record<NonNullable<ProgressBarProps['tone']>, string> = {
  action: 'bg-action',
  accent: 'bg-accent',
}

export function ProgressBar({ value, tone = 'action', className = '' }: ProgressBarProps) {
  return (
    <div
      className={`h-1.5 overflow-hidden rounded-full bg-[#edf0eb] ${className}`}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <span
        className={`block h-full rounded-full transition-[width] duration-500 ease-out ${fillTone[tone]}`}
        style={{ width: `${value}%` }}
      />
    </div>
  )
}
