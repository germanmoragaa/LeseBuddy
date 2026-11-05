import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, BookOpen, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { createArticle } from '../../lib/api'

const ARTICLE_TEXT_MAX_LENGTH = 50_000

export function AddText() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const wordCount = text.split(/\s+/).filter(Boolean).length
  const isTooLong = text.length > ARTICLE_TEXT_MAX_LENGTH

  const mutation = useMutation({
    mutationFn: createArticle,
    onSuccess: (article) => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      navigate(`/app/reader/${article.id}`)
    },
  })

  const tabClass = (isActive: boolean, disabled = false) =>
    `min-h-[34px] rounded-sm px-3 text-[10px] font-bold ${
      disabled
        ? 'cursor-not-allowed text-muted/50'
        : isActive
          ? 'bg-white text-brand shadow-[0_2px_8px_rgb(33_46_36_/_0.06)]'
          : 'text-muted'
    }`

  return (
    <div className="min-h-screen bg-[#f1f0eb] p-7">
      <Button variant="ghost" onClick={() => navigate('/app')}>
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
          <button type="button" className={tabClass(true)} aria-current="true">
            Paste text
          </button>
          <button
            type="button"
            className={tabClass(false, true)}
            disabled
            title="Coming soon — URL import isn't available yet"
          >
            Enter a URL <span className="ml-1 text-[8px] font-normal">(Coming soon)</span>
          </button>
        </div>

        <div className="grid gap-3.5 text-left">
          <label className="block">
            <span className="mb-1.5 flex justify-between text-[10px] font-bold">
              Title <small className="font-normal text-muted">Optional</small>
            </span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
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
          {isTooLong && (
            <p role="alert" className="text-[10px] text-danger">
              Your text is too long ({text.length.toLocaleString()} characters). Please keep it
              under {ARTICLE_TEXT_MAX_LENGTH.toLocaleString()} characters.
            </p>
          )}
        </div>

        <div className="mt-3 flex gap-2.5 rounded-sm bg-accent-soft p-3.5 text-left text-[9px] text-[#756b4b]">
          <Sparkles size={17} aria-hidden="true" className="shrink-0" />
          <span>Importing from a URL isn't available yet — paste the text instead.</span>
        </div>

        {mutation.isError && (
          <p role="alert" className="mt-4 rounded-sm bg-surface-coral px-3.5 py-2.5 text-xs text-[#8a5141]">
            Something went wrong. Please try again.
          </p>
        )}

        <Button
          className="mt-5 w-full"
          disabled={text.trim().length === 0 || isTooLong || mutation.isPending}
          onClick={() =>
            mutation.mutate({ title: title.trim() || undefined, original_text: text })
          }
        >
          {mutation.isPending ? 'Creating…' : 'Create reading space'}{' '}
          <ArrowRight size={18} aria-hidden="true" />
        </Button>
        <p className="mt-3 text-[8px] text-muted">Your text stays in your private reading library.</p>
      </div>
    </div>
  )
}
