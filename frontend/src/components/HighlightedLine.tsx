import { CodePointIndex } from '../lib/textOffsets'

interface HighlightedLineProps {
  line: string
  // Code-point offsets within `line` (as the backend sends them); null = nothing to mark.
  start: number | null
  end: number | null
  className?: string
}

// Renders a context line with the saved word marked. Offsets are code points, so the slice
// goes through CodePointIndex like every other backend offset (see lib/textOffsets.ts).
export function HighlightedLine({ line, start, end, className }: HighlightedLineProps) {
  const codePointLength = Array.from(line).length
  if (start === null || end === null || start < 0 || end > codePointLength || start >= end) {
    return <p className={className}>{line}</p>
  }
  const index = new CodePointIndex(line)
  return (
    <p className={className}>
      {index.slice(line, 0, start)}
      <mark className="rounded-[2px] bg-accent-soft px-0.5 font-semibold text-ink">
        {index.slice(line, start, end)}
      </mark>
      {index.slice(line, end, codePointLength)}
    </p>
  )
}
