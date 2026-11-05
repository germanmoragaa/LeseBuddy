import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpen, Plus } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { listArticles } from '../../lib/api'

const RECENT_COUNT = 5

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

export function RecentReadingList() {
  const navigate = useNavigate()
  const recentQuery = useQuery({
    queryKey: ['articles', 'recent-list'],
    queryFn: () => listArticles({ page: 1, pageSize: RECENT_COUNT }),
  })

  const items = recentQuery.data?.items ?? []

  return (
    <Card className="mt-4 p-5.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your library
          </span>
          <h2 className="mt-1.5 text-[19px]">Recent reading</h2>
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
      <div className="mt-3">
        {recentQuery.isPending && <p className="py-6 text-center text-sm text-muted">Loading…</p>}

        {recentQuery.isError && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-sm text-danger" role="alert">
              Couldn't load your recent reading.
            </p>
            <Button variant="secondary" onClick={() => recentQuery.refetch()}>
              Try again
            </Button>
          </div>
        )}

        {recentQuery.data && items.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-xs text-muted">You haven't added any texts yet.</p>
            <Button onClick={() => navigate('/app/reader/new')}>
              <Plus size={18} aria-hidden="true" /> Add a text
            </Button>
          </div>
        )}

        {items.map((article) => (
          <button
            type="button"
            key={article.id}
            onClick={() => navigate(`/app/reader/${article.id}`)}
            className="grid min-h-16 w-full grid-cols-[36px_1fr_20px] items-center gap-3 border-t border-line py-2.5 text-left hover:bg-[#fdfdfb] lg:grid-cols-[36px_minmax(200px,1.7fr)_80px_20px]"
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
            </span>
            <span className="hidden text-[9px] text-muted lg:block">
              {formatDate(article.created_at)}
            </span>
            <ArrowRight size={17} aria-hidden="true" className="text-muted" />
          </button>
        ))}
      </div>
    </Card>
  )
}
