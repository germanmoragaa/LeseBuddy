import { Volume2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { ProgressBar } from '../../components/ProgressBar'
import { mockFlashcard, mockFlashcardQueueLength } from '../../mocks/flashcards'
import type { ReviewRating } from '../../types/flashcards'
import { RatingButtons } from './RatingButtons'
import { SessionComplete } from './SessionComplete'

export function Flashcards() {
  const navigate = useNavigate()
  const [revealed, setRevealed] = useState(false)
  const [step, setStep] = useState(3)
  const [complete, setComplete] = useState(false)

  const rate = (_rating: ReviewRating) => {
    if (step >= mockFlashcardQueueLength) {
      setComplete(true)
    } else {
      setStep((value) => value + 1)
      setRevealed(false)
    }
  }

  if (complete) {
    return (
      <SessionComplete
        onReviewAnother={() => {
          setComplete(false)
          setStep(1)
          setRevealed(false)
        }}
      />
    )
  }

  const card = mockFlashcard
  const [beforeMark, ...afterParts] = card.exampleSentence.split(card.highlightedForm)
  const afterMark = afterParts.join(card.highlightedForm)

  return (
    <div className="min-h-screen bg-[#f4f2ec] px-6 py-10">
      <div className="mx-auto mb-4.5 flex max-w-[980px] items-start justify-between">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Daily review
          </span>
          <h1 className="my-1.5 text-[26px] tracking-tight">Time for a little practice</h1>
          <p className="m-0 text-[11px] text-muted">
            A few minutes today can make tomorrow's reading easier.
          </p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/app')}>
          Exit session
        </Button>
      </div>

      <div className="mx-auto mb-8 grid max-w-[980px] grid-cols-[100px_1fr_90px] items-center gap-3.5 text-[10px] text-muted">
        <span>
          <strong className="text-ink">
            {step} of {mockFlashcardQueueLength}
          </strong>{' '}
          cards
        </span>
        <ProgressBar value={(step / mockFlashcardQueueLength) * 100} />
        <span className="text-right">~3 min left</span>
      </div>

      <div
        className={`relative mx-auto flex max-w-[620px] flex-col rounded-lg border border-line bg-white px-6 pb-9 pt-7 shadow-[0_18px_55px_rgb(43_56_45_/_0.08)] sm:px-11 ${
          revealed ? 'min-h-[520px]' : 'min-h-[460px]'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-extrabold uppercase tracking-wide text-action">
            German
          </span>
          <Button variant="icon" aria-label={`Listen to pronunciation of ${card.word}`}>
            <Volume2 size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <h2 className="text-[34px] tracking-tight">{card.word}</h2>
          <span className="mt-1.5 text-[11px] italic text-muted">{card.partOfSpeech}</span>
          <p className="my-9 rounded-sm bg-[#f7f6f2] px-4 py-3.5 font-serif text-base">
            {beforeMark}
            <mark className="bg-surface-mint-strong text-brand">{card.highlightedForm}</mark>
            {afterMark}
          </p>
          {!revealed ? (
            <small className="text-[9px] text-muted">
              Think of the meaning before revealing the answer.
            </small>
          ) : (
            <div className="w-full animate-[fade_0.2s_ease] border-t border-line pt-6">
              <span className="text-[9px] uppercase tracking-wide text-muted">
                English meaning
              </span>
              <h3 className="my-1.5 text-[23px] text-brand">{card.meaning}</h3>
              <p className="m-0 text-[11px] text-muted">{card.meaningTranslation}</p>
              {card.grammarNote && (
                <div className="mt-4.5 flex justify-center gap-2 rounded-sm bg-surface-lavender p-2.5 text-[9px] text-[#655f73]">
                  <strong>Grammar note</strong>
                  <span>{card.grammarNote}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {!revealed && (
          <Button className="w-full" onClick={() => setRevealed(true)}>
            Reveal answer
          </Button>
        )}
      </div>

      {revealed && <RatingButtons onRate={rate} />}

      <div className="mt-6 text-center text-[8px] text-[#aaaaaa]">
        Press <kbd className="rounded-[4px] border border-line bg-white px-1 py-0.5">Space</kbd>{' '}
        to reveal · Use{' '}
        <kbd className="rounded-[4px] border border-line bg-white px-1 py-0.5">1–4</kbd> to rate
      </div>
    </div>
  )
}
