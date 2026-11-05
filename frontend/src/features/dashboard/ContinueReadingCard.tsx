import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpen, Plus } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { listArticles } from '../../lib/api'

const WORDS_PER_MINUTE = 200

export function ContinueReadingCard() {
  const navigate = useNavigate()
  const recentQuery = useQuery({
    queryKey: ['articles', 'recent'],
    queryFn: () => listArticles({ page: 1, pageSize: 1 }),
  })

  const article = recentQuery.data?.items?.[0]

  return (
    <Card className="p-5.5">
      <div className="flex items-center gap-2 text-xs font-bold">
        <span className="grid h-[29px] w-[29px] place-items-center rounded-[8px] bg-surface-mint text-brand">
          <BookOpen size={17} aria-hidden="true" />
        </span>
        Pick up where you left off
      </div>

      {recentQuery.isPending && (
        <p className="mt-4.5 text-center text-sm text-muted">Loading…</p>
      )}

      {recentQuery.isError && (
        <div className="mt-4.5 flex flex-col items-center gap-3 text-center">
          <p className="text-sm text-danger" role="alert">
            Couldn't load your reading library.
          </p>
          <Button variant="secondary" onClick={() => recentQuery.refetch()}>
            Try again
          </Button>
        </div>
      )}

      {recentQuery.data && !article && (
        <div className="mt-4.5 flex flex-col items-center gap-3 text-center">
          <p className="text-xs text-muted">
            You haven't added any texts yet. Paste a German text to get started.
          </p>
          <Button onClick={() => navigate('/app/reader/new')}>
            <Plus size={18} aria-hidden="true" /> Add a text
          </Button>
        </div>
      )}

      {article && (
        <div className="mt-4.5 grid gap-5.5 sm:grid-cols-[160px_1fr]">
          <div
            className="relative min-h-[150px] overflow-hidden rounded-[12px] bg-[#f2e6d0] text-brand sm:min-h-[228px]"
            aria-hidden="true"
          >
            <span className="absolute left-[17px] top-[18px] text-[9px] font-extrabold tracking-widest">
              LESE
              <br />
              PAUSE
            </span>
          </div>
          <div className="self-center">
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="plain">
                {Math.max(1, Math.ceil(article.word_count / WORDS_PER_MINUTE))} min read
              </Badge>
            </div>
            <h2 className="my-3 max-w-[460px] text-[clamp(19px,2vw,25px)] leading-tight tracking-tight">
              {article.title ?? 'Untitled text'}
            </h2>
            {article.excerpt && <p className="mb-5 text-xs text-muted">{article.excerpt}</p>}
            <Button className="mt-5" onClick={() => navigate(`/app/reader/${article.id}`)}>
              Continue reading <ArrowRight size={17} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}
