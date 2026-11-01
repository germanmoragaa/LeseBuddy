import { ArrowLeft, Bookmark, Check, Focus, MoreHorizontal, Type } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { mockArticle, mockArticleParagraphs, mockWordExplanations } from '../../mocks/reader'
import { ExplanationPanel } from './ExplanationPanel'
import { Word } from './Word'

export function Reader() {
  const navigate = useNavigate()
  const [selectedWord, setSelectedWord] = useState<string | null>('wohltuend')
  const [saved, setSaved] = useState(false)

  const explanation = selectedWord ? mockWordExplanations[selectedWord] : undefined

  return (
    <div className="min-h-screen bg-[#f3f2ee]">
      <div className="grid min-h-[70px] grid-cols-[40px_minmax(280px,1fr)_auto_40px_40px] items-center gap-2.5 border-b border-line bg-white px-6">
        <Button variant="icon" aria-label="Back to dashboard" onClick={() => navigate('/')}>
          <ArrowLeft size={18} aria-hidden="true" />
        </Button>
        <div>
          <strong className="block text-[13px]">{mockArticle.title}</strong>
          <span className="mt-0.5 block text-[9px] text-muted">Example German article</span>
        </div>
        <div className="hidden items-center gap-4 text-[10px] text-muted sm:flex">
          <Badge>{mockArticle.levelLabel}</Badge>
          <span>{mockArticle.wordCount} words</span>
          <span>{mockArticle.readMinutes} min read</span>
        </div>
        <Button variant="icon" aria-label="Bookmark this article">
          <Bookmark size={18} aria-hidden="true" />
        </Button>
        <Button variant="icon" aria-label="More options">
          <MoreHorizontal size={18} aria-hidden="true" />
        </Button>
      </div>

      <div className="flex min-h-[50px] items-center justify-end gap-1 overflow-x-auto border-b border-line bg-white px-6">
        <div className="flex items-center gap-1 rounded-[7px] bg-[#f4f3ef] pr-1">
          <span className="pl-2.5 text-muted">
            <Type size={17} aria-hidden="true" />
          </span>
          <button type="button" className="min-h-8 rounded-[7px] px-2.5 text-[10px] font-semibold text-ink">
            A−
          </button>
          <button type="button" className="min-h-8 rounded-[7px] px-2.5 text-[10px] font-semibold text-ink">
            A+
          </button>
        </div>
        <div className="mx-1 h-5 w-px bg-line" />
        <button
          type="button"
          className="inline-flex min-h-8 items-center gap-1.5 rounded-[7px] px-2.5 text-[10px] font-semibold text-muted hover:bg-[#f4f3ef] hover:text-ink"
        >
          <Bookmark size={17} aria-hidden="true" /> Show saved words
        </button>
        <button
          type="button"
          className="inline-flex min-h-8 items-center gap-1.5 rounded-[7px] px-2.5 text-[10px] font-semibold text-muted hover:bg-[#f4f3ef] hover:text-ink"
        >
          <Focus size={17} aria-hidden="true" /> Focus mode
        </button>
      </div>

      <div className="grid justify-center gap-5 p-6 lg:grid-cols-[minmax(500px,810px)_344px]">
        <main className="rounded-[3px] border border-line bg-white px-6 py-10 shadow-[0_8px_40px_rgb(49_52_45_/_0.05)] sm:px-16 sm:py-16">
          <div className="text-[10px] font-bold uppercase tracking-wide text-action">
            {mockArticle.category} <span className="mx-1 text-[#c0c3bc]">·</span>{' '}
            {mockArticle.dateLabel}
          </div>
          <h1 className="my-3 max-w-[600px] text-[clamp(30px,3.4vw,44px)] leading-tight tracking-tight">
            {mockArticle.title}
          </h1>
          <p className="m-0 text-sm text-muted">{mockArticle.deck}</p>
          <div className="my-8 flex items-center gap-2 text-action">
            <span className="h-px flex-1 bg-line" />
            <span className="h-px flex-1 bg-line" />
          </div>
          <div className="font-serif text-[19px] leading-[1.82] text-[#343831]">
            {mockArticleParagraphs.map((paragraph, index) => (
              <p key={index} className="mb-7">
                {paragraph.map((part, partIndex) =>
                  part.wordKey ? (
                    <Word
                      key={partIndex}
                      active={selectedWord === part.wordKey}
                      onClick={() => setSelectedWord(part.wordKey!)}
                    >
                      {part.text}
                    </Word>
                  ) : (
                    <span key={partIndex}>{part.text}</span>
                  ),
                )}
              </p>
            ))}
          </div>
          <div className="mt-12 grid grid-cols-[38px_1fr_auto] items-center gap-3.5 rounded-sm border border-[#dfece2] bg-[#f7faf7] p-5">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-surface-mint text-brand">
              <Check size={20} aria-hidden="true" />
            </span>
            <div>
              <h3 className="m-0 text-[13px]">You're at the end of this reading.</h3>
              <p className="mt-1 text-[10px] text-muted">You saved 4 useful words along the way.</p>
            </div>
            <Button>Mark as finished</Button>
          </div>
        </main>

        {selectedWord && explanation && (
          <ExplanationPanel
            word={selectedWord}
            explanation={explanation}
            saved={saved}
            onToggleSaved={() => setSaved((value) => !value)}
            onClose={() => setSelectedWord(null)}
          />
        )}
      </div>
    </div>
  )
}
