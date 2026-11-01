import type { ReactNode } from 'react'

interface WordProps {
  active: boolean
  onClick: () => void
  children: ReactNode
}

export function Word({ active, onClick, children }: WordProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline rounded-[3px] border-b px-px font-[inherit] leading-[inherit] text-inherit transition-colors hover:bg-[#f0f5ef] ${
        active ? 'border-b-2 border-action bg-surface-mint-strong' : 'border-b-[#8ab89a]'
      }`}
    >
      {children}
    </button>
  )
}
