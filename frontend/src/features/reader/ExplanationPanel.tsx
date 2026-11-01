import { Check, Plus, Sparkles, Volume2, X } from 'lucide-react'

import { Button } from '../../components/Button'
import type { WordExplanation } from '../../types/reader'

interface ExplanationPanelProps {
  word: string
  explanation: WordExplanation
  saved: boolean
  onToggleSaved: () => void
  onClose: () => void
}

export function ExplanationPanel({
  word,
  explanation,
  saved,
  onToggleSaved,
  onClose,
}: ExplanationPanelProps) {
  return (
    <aside className="sticky top-6 rounded-md border border-line bg-white p-5 shadow-card lg:w-[344px]">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
          In context
        </span>
        <Button variant="icon" aria-label="Close word explanation" onClick={onClose}>
          <X size={18} aria-hidden="true" />
        </Button>
      </div>

      <div className="my-5 flex items-center justify-between">
        <div>
          <h2 className="text-[28px] tracking-tight">{word}</h2>
          <span className="mt-1 block text-[10px] italic text-muted">
            {explanation.partOfSpeech}
          </span>
        </div>
        <Button variant="icon" aria-label={`Listen to pronunciation of ${word}`}>
          <Volume2 size={20} aria-hidden="true" />
        </Button>
      </div>

      <div className="border-t border-line py-3.5">
        <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
          English meaning
        </span>
        <strong className="text-[15px]">{explanation.meaning}</strong>
      </div>

      <div className="rounded-sm bg-[#f7f6f2] p-3.5">
        <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
          In this sentence
        </span>
        <p className="text-[11px] italic leading-relaxed text-ink">
          “
          {explanation.contextSentence
            .split(word)
            .map((chunk, index, parts) => (
              <span key={index}>
                {chunk}
                {index < parts.length - 1 && (
                  <mark className="bg-surface-mint-strong">{word}</mark>
                )}
              </span>
            ))}
          ”
        </p>
        <small className="mt-2 block text-[9px] leading-relaxed text-muted">
          “{explanation.contextTranslation}”
        </small>
      </div>

      {explanation.note && (
        <div className="mt-3.5 flex items-start gap-2.5 rounded-sm bg-surface-lavender p-3.5">
          <span className="grid h-[26px] w-[26px] shrink-0 place-items-center rounded-sm bg-white text-[#63568d]">
            <Sparkles size={15} aria-hidden="true" />
          </span>
          <div>
            <strong className="text-[10px]">Language note</strong>
            <p className="mt-1 text-[10px] leading-relaxed text-[#625e6d]">{explanation.note}</p>
          </div>
        </div>
      )}

      {explanation.example && (
        <div className="mt-3.5">
          <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
            Another example
          </span>
          <p className="text-[11px] font-semibold text-ink">{explanation.example}</p>
          <small className="mt-2 block text-[9px] leading-relaxed text-muted">
            {explanation.exampleTranslation}
          </small>
        </div>
      )}

      <Button className="mt-4 w-full" onClick={onToggleSaved}>
        {saved ? <Check size={18} aria-hidden="true" /> : <Plus size={18} aria-hidden="true" />}
        {saved ? 'Saved to vocabulary' : 'Save to vocabulary'}
      </Button>

      <div className="mt-4 flex items-center justify-center gap-1.5 border-t border-line pt-3 text-[8px] text-[#9a9d96]">
        <Sparkles size={13} aria-hidden="true" /> AI-generated explanation · It may make mistakes.
      </div>
    </aside>
  )
}
