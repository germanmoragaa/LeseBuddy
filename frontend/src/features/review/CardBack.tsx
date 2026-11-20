import { Music } from 'lucide-react'

import { HighlightedLine } from '../../components/HighlightedLine'
import type { FlashcardBack } from '../../types/flashcards'
import { cardMeanings } from './cardMeanings'

export function CardBack({ back }: { back: FlashcardBack }) {
  const meanings = cardMeanings(back)
  const [primary, ...others] = meanings
  const example = back.example
  const exampleLine = example?.line ?? back.context_sentence

  return (
    <div
      data-testid="card-back"
      className="mt-9 w-full animate-[fade_0.2s_ease] border-t border-line pt-6"
    >
      <span className="text-[9px] uppercase tracking-wide text-muted">
        {primary?.source === 'machine' ? 'In this context' : 'Meaning'}
      </span>
      <h3 className="my-1.5 text-[23px] text-brand">{primary?.text ?? '—'}</h3>
      {others.length > 0 && (
        <p className="m-0 text-[12px] text-muted">
          <span className="sr-only">Other meanings: </span>
          {others.map((meaning) => meaning.text).join(', ')}
        </p>
      )}

      {exampleLine && (
        <figure className="mx-0 my-4.5 rounded-sm bg-[#f7f6f2] px-4 py-3.5 text-left">
          <HighlightedLine
            line={exampleLine}
            start={example?.highlight_start ?? null}
            end={example?.highlight_end ?? null}
            className="m-0 font-serif text-base"
          />
          {example?.translation && (
            <p className="m-0 mt-1.5 text-[12px] italic text-muted">{example.translation}</p>
          )}
          {example?.song && (
            <figcaption className="mt-3 flex items-center gap-2 text-[11px] text-muted">
              {example.song.cover_url ? (
                <img
                  src={example.song.cover_url}
                  alt=""
                  className="h-7 w-7 rounded-sm object-cover"
                  loading="lazy"
                />
              ) : (
                <span className="grid h-7 w-7 place-items-center rounded-sm bg-surface-lavender text-brand">
                  <Music size={14} aria-hidden="true" />
                </span>
              )}
              <span>
                <span className="font-semibold text-ink">{example.song.title}</span> ·{' '}
                {example.song.artist}
              </span>
            </figcaption>
          )}
        </figure>
      )}
    </div>
  )
}
