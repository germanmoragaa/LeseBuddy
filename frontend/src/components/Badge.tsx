import type { HTMLAttributes, ReactNode } from 'react'

type BadgeTone = 'mint' | 'plain' | 'lavender' | 'yellow' | 'coral'

const tones: Record<BadgeTone, string> = {
  mint: 'bg-surface-mint text-brand',
  plain: 'bg-[#f4f3ef] text-muted',
  lavender: 'bg-surface-lavender text-[#65558a]',
  yellow: 'bg-accent-soft text-[#81620b]',
  coral: 'bg-surface-coral text-[#8a5141]',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  children: ReactNode
}

export function Badge({ tone = 'mint', className = '', children, ...props }: BadgeProps) {
  return (
    <span
      className={`inline-flex w-max items-center rounded-[6px] px-2 py-1 text-[9px] font-bold ${tones[tone]} ${className}`}
      {...props}
    >
      {children}
    </span>
  )
}
