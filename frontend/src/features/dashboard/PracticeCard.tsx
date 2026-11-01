import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { mockDueFlashcardsCount, mockPracticeWords } from '../../mocks/dashboard'

export function PracticeCard() {
  const navigate = useNavigate()

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Quick practice
          </span>
          <h3 className="mt-1.5 text-[15px] leading-snug">Words ready for a little practice</h3>
        </div>
        <span className="whitespace-nowrap rounded-[6px] bg-accent-soft px-2 py-1 text-[9px] font-bold text-[#775f0f]">
          {mockDueFlashcardsCount} due
        </span>
      </div>
      <div className="my-3.5">
        {mockPracticeWords.map((item, index) => (
          <button
            type="button"
            key={item.word}
            onClick={() => navigate('/flashcards')}
            className="grid w-full min-h-12 grid-cols-[27px_1fr_auto] items-center gap-2.5 border-b border-line py-2 text-left last:border-b-0"
          >
            <span className="text-[9px] text-[#adb0a9]">0{index + 1}</span>
            <span>
              <strong className="block text-[11px]">{item.word}</strong>
              <small className="mt-0.5 block text-[9px] text-muted">{item.translation}</small>
            </span>
            <ArrowRight size={16} aria-hidden="true" className="text-muted" />
          </button>
        ))}
      </div>
      <Button variant="secondary" className="w-full" onClick={() => navigate('/flashcards')}>
        Review all {mockDueFlashcardsCount} cards
      </Button>
    </Card>
  )
}
