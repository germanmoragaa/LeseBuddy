import { forwardRef } from 'react'
import type { KeyboardEvent, MouseEvent, ReactNode } from 'react'

interface WordProps {
  isActive: boolean
  isSelected: boolean
  isSeparableVerbPart: boolean
  onMouseDown: (event: MouseEvent<HTMLButtonElement>) => void
  onMouseEnter: () => void
  onClick: (event: MouseEvent<HTMLButtonElement>) => void
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
  children: ReactNode
}

export const Word = forwardRef<HTMLButtonElement, WordProps>(function Word(
  { isActive, isSelected, isSeparableVerbPart, onMouseDown, onMouseEnter, onClick, onKeyDown, children },
  ref,
) {
  const tone = isSelected
    ? 'bg-accent-soft decoration-transparent'
    : isSeparableVerbPart
      ? 'bg-surface-mint decoration-brand'
      : 'decoration-line hover:bg-black/5'

  return (
    <button
      ref={ref}
      type="button"
      tabIndex={isActive ? 0 : -1}
      onMouseDown={onMouseDown}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      onKeyDown={onKeyDown}
      className={`-mx-0.5 rounded-[3px] px-0.5 underline decoration-dotted decoration-1 underline-offset-2 outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action ${tone}`}
    >
      {children}
    </button>
  )
})
