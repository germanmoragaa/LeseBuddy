import { ExternalLink, Volume2, X } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import type { VocabularyItem } from '../../types/vocabulary'
import { StatusBadge } from './StatusBadge'

interface VocabularyDetailDrawerProps {
  item: VocabularyItem
  onClose: () => void
}

export function VocabularyDetailDrawer({ item, onClose }: VocabularyDetailDrawerProps) {
  const navigate = useNavigate()

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close vocabulary detail"
        onClick={onClose}
        className="absolute inset-0 w-full border-0 bg-black/30"
      />
      <aside className="absolute inset-y-0 right-0 w-full max-w-[440px] overflow-y-auto bg-white p-6 shadow-[-20px_0_60px_rgb(25_40_31_/_0.14)]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Vocabulary detail
          </span>
          <Button variant="icon" aria-label="Close vocabulary detail" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="border-b border-line py-7">
          <StatusBadge status={item.status} />
          <h2 className="mb-1 mt-2.5 text-[32px] tracking-tight">{item.word}</h2>
          <p className="mb-4 text-muted">{item.meaning}</p>
          <Button variant="secondary">
            <Volume2 size={18} aria-hidden="true" /> Listen
          </Button>
        </div>

        <div className="border-b border-line py-5">
          <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
            Original context
          </span>
          <p className="text-[11px] leading-relaxed text-ink">{item.exampleSentence}</p>
          <button
            type="button"
            onClick={() => navigate('/reader')}
            className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-bold text-action"
          >
            Open in original text <ExternalLink size={14} aria-hidden="true" />
          </button>
        </div>

        {item.grammarNote && (
          <div className="border-b border-line py-5">
            <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
              Grammar note
            </span>
            <p className="text-[11px] leading-relaxed text-ink">{item.grammarNote}</p>
          </div>
        )}

        <div className="grid grid-cols-2 py-5">
          <span>
            <small className="block text-[9px] text-muted">Saved</small>
            <strong className="mt-1 block text-[11px]">{item.savedDateLabel}</strong>
          </span>
          <span>
            <small className="block text-[9px] text-muted">Next review</small>
            <strong className="mt-1 block text-[11px]">{item.nextReviewLabel}</strong>
          </span>
        </div>

        <Button className="w-full" onClick={() => navigate('/flashcards')}>
          Practise this word
        </Button>
      </aside>
    </div>
  )
}
