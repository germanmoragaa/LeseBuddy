import type { VocabularyStatus } from '../../types/vocabulary'

const statusStyles: Record<VocabularyStatus, { label: string; className: string }> = {
  new: { label: 'New', className: 'bg-surface-mint text-brand' },
  learning: { label: 'Learning', className: 'bg-surface-lavender text-[#65558a]' },
  'due-soon': { label: 'Due soon', className: 'bg-accent-soft text-[#81620b]' },
  review: { label: 'Review', className: 'bg-surface-coral text-[#8a5141]' },
}

export function StatusBadge({ status }: { status: VocabularyStatus }) {
  const { label, className } = statusStyles[status]
  return (
    <span className={`inline-flex w-max rounded-[6px] px-2 py-1 text-[8px] font-semibold ${className}`}>
      {label}
    </span>
  )
}
