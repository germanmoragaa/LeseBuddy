import { ArrowLeft, ArrowRight, BookOpen, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'

export function AddText() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'paste' | 'url'>('paste')
  const [text, setText] = useState('')
  const wordCount = text.split(/\s+/).filter(Boolean).length

  const tabClass = (isActive: boolean) =>
    `min-h-[34px] rounded-sm px-3 text-[10px] font-bold ${
      isActive ? 'bg-white text-brand shadow-[0_2px_8px_rgb(33_46_36_/_0.06)]' : 'text-muted'
    }`

  return (
    <div className="min-h-screen bg-[#f1f0eb] p-7">
      <Button variant="ghost" onClick={() => navigate('/')}>
        <ArrowLeft size={18} aria-hidden="true" /> Back to dashboard
      </Button>

      <div className="mx-auto mt-4 max-w-[670px] rounded-[22px] border border-line bg-white px-7 py-11 text-center shadow-card sm:px-14">
        <span className="mx-auto grid h-[50px] w-[50px] place-items-center rounded-[15px] bg-surface-mint text-brand">
          <BookOpen size={24} aria-hidden="true" />
        </span>
        <span className="mt-5 block text-[12px] font-bold uppercase tracking-wide text-muted">
          New reading
        </span>
        <h1 className="my-2 text-[29px] tracking-tight">What would you like to read today?</h1>
        <p className="mx-auto max-w-[450px] text-[11px] leading-relaxed text-muted">
          Bring a German text you care about. We'll help you understand it as you go.
        </p>

        <div className="mx-auto my-6 flex w-max gap-1 rounded-sm bg-[#efeee9] p-1">
          <button type="button" className={tabClass(mode === 'paste')} onClick={() => setMode('paste')}>
            Paste text
          </button>
          <button type="button" className={tabClass(mode === 'url')} onClick={() => setMode('url')}>
            Enter a URL
          </button>
        </div>

        {mode === 'paste' ? (
          <div className="grid gap-3.5 text-left">
            <label className="block">
              <span className="mb-1.5 flex justify-between text-[10px] font-bold">
                Title <small className="font-normal text-muted">Optional</small>
              </span>
              <input
                placeholder="Give your text a title"
                className="h-[43px] w-full rounded-sm border border-line px-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-bold">German text</span>
              <textarea
                placeholder="Paste a German article, paragraph, or passage here…"
                value={text}
                onChange={(event) => setText(event.target.value)}
                className="min-h-[180px] w-full resize-y rounded-sm border border-line px-3.5 pt-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
              />
              <small className="mt-1 block text-right text-[8px] text-muted">
                {wordCount} words
              </small>
            </label>
          </div>
        ) : (
          <div className="grid gap-3.5 text-left">
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-bold">Article URL</span>
              <input
                placeholder="https://example.com/article"
                className="h-[43px] w-full rounded-sm border border-line px-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
              />
            </label>
            <div className="flex gap-2.5 rounded-sm bg-accent-soft p-3.5 text-[9px] text-[#756b4b]">
              <Sparkles size={17} aria-hidden="true" className="shrink-0" />
              <span>
                Only public, accessible pages can be imported. Some websites may not be supported.
              </span>
            </div>
          </div>
        )}

        <Button className="mt-5 w-full" onClick={() => navigate('/reader')}>
          Create reading space <ArrowRight size={18} aria-hidden="true" />
        </Button>
        <p className="mt-3 text-[8px] text-muted">Your text stays in your private reading library.</p>
      </div>
    </div>
  )
}
