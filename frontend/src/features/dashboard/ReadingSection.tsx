import { ArrowRight, BookOpen, Plus } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { ProgressBar } from '../../components/ProgressBar'
import { formatRelativeTime } from '../../lib/relativeTime'
import type { ArticleListItem } from '../../types/article'
import { useRecentArticles } from './useRecentArticles'

const WORDS_PER_MINUTE = 200

function estimatedReadMinutes(wordCount: number) {
  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE))
}

function activitySummary(article: ArticleListItem) {
  return article.last_opened_at
    ? `Opened ${formatRelativeTime(article.last_opened_at)}`
    : `Added ${formatRelativeTime(article.created_at)}`
}

export function ReadingSection() {
  const navigate = useNavigate()
  const recentQuery = useRecentArticles()

  const items = recentQuery.data?.items ?? []
  const [featured, ...rest] = items

  return (
    <Card className="p-5.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your library
          </span>
          <h2 className="mt-1.5 text-[19px]">Continue reading</h2>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={() => navigate('/app/reader')}
            className="inline-flex items-center gap-1 text-[11px] font-bold text-action"
          >
            View all <ArrowRight size={14} aria-hidden="true" />
          </button>
        )}
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

      {recentQuery.data && items.length === 0 && (
        <div className="mt-4.5 flex flex-col items-center gap-3 text-center">
          <p className="text-xs text-muted">
            You haven't added any texts yet. Paste a German text to get started.
          </p>
          <Button onClick={() => navigate('/app/reader/new')}>
            <Plus size={18} aria-hidden="true" /> Add a text
          </Button>
        </div>
      )}

      {featured && (
        <div className="mt-4.5 grid gap-5.5 rounded-[12px] bg-surface-mint/40 p-4 sm:grid-cols-[160px_1fr]">
          <div
            className="relative min-h-[150px] overflow-hidden rounded-[12px] bg-[#f2e6d0] text-brand sm:min-h-[200px]"
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
              <Badge tone="plain">{estimatedReadMinutes(featured.word_count)} min read</Badge>
              <Badge tone="mint">{activitySummary(featured)}</Badge>
            </div>
            <h3 className="my-3 max-w-[460px] text-[clamp(19px,2vw,25px)] leading-tight tracking-tight">
              {featured.title ?? 'Untitled text'}
            </h3>
            {featured.excerpt && <p className="mb-4 text-xs text-muted">{featured.excerpt}</p>}
            {featured.progress_percent !== null && (
              <ProgressBar
                value={featured.progress_percent}
                tone="accent"
                className="mb-5 max-w-[320px]"
              />
            )}
            <Button onClick={() => navigate(`/app/reader/${featured.id}`)}>
              Continue reading <ArrowRight size={17} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}

      {rest.length > 0 && (
        <div className="mt-2">
          {rest.map((article) => (
            <button
              type="button"
              key={article.id}
              onClick={() => navigate(`/app/reader/${article.id}`)}
              className="grid min-h-16 w-full grid-cols-[36px_1fr_20px] items-center gap-3 border-t border-line py-2.5 text-left hover:bg-[#fdfdfb] lg:grid-cols-[36px_minmax(200px,1.7fr)_110px_20px]"
            >
              <span className="grid h-9 w-8 place-items-center rounded-[5px_8px_8px_5px] bg-[#f2e6d0] text-brand">
                <BookOpen size={18} aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <strong className="block truncate text-[11px]">
                  {article.title ?? 'Untitled text'}
                </strong>
                <small className="mt-0.5 block truncate text-[9px] text-muted">
                  {article.excerpt}
                </small>
                {article.progress_percent !== null && (
                  <ProgressBar value={article.progress_percent} className="mt-1.5 max-w-[160px]" />
                )}
              </span>
              <span className="hidden text-[9px] text-muted lg:block">
                {activitySummary(article)}
              </span>
              <ArrowRight size={17} aria-hidden="true" className="text-muted" />
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}
