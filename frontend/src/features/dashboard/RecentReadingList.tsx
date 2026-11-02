import { ArrowRight, BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Badge } from '../../components/Badge'
import { Card } from '../../components/Card'
import { ProgressBar } from '../../components/ProgressBar'
import { mockRecentArticles } from '../../mocks/dashboard'

export function RecentReadingList() {
  const navigate = useNavigate()

  return (
    <Card className="mt-4 p-5.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your library
          </span>
          <h2 className="mt-1.5 text-[19px]">Recent reading</h2>
        </div>
        <button type="button" className="inline-flex items-center gap-1 text-[11px] font-bold text-action">
          View all <ArrowRight size={14} aria-hidden="true" />
        </button>
      </div>
      <div className="mt-3">
        {mockRecentArticles.map((article) => (
          <button
            type="button"
            key={article.id}
            onClick={() => navigate('/app/reader')}
            className="grid min-h-16 w-full grid-cols-[36px_1fr_20px] items-center gap-3 border-t border-line py-2.5 text-left hover:bg-[#fdfdfb] lg:grid-cols-[36px_minmax(200px,1.7fr)_90px_minmax(130px,.8fr)_80px_20px]"
          >
            <span className="grid h-9 w-8 place-items-center rounded-[5px_8px_8px_5px] bg-[#f2e6d0] text-brand">
              <BookOpen size={18} aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <strong className="block truncate text-[11px]">{article.title}</strong>
              <small className="mt-0.5 block text-[9px] text-muted">{article.category}</small>
            </span>
            <span className="hidden lg:block">
              <Badge>{article.level}</Badge>
            </span>
            <span className="hidden lg:block">
              <small className="block text-[9px] text-muted">Progress</small>
              <span className="mt-1 grid grid-cols-[1fr_28px] items-center gap-1.5">
                <ProgressBar value={article.percentComplete} />
                <b className="text-[9px]">{article.percentComplete}%</b>
              </span>
            </span>
            <span className="hidden text-[9px] text-muted lg:block">{article.lastOpenedLabel}</span>
            <ArrowRight size={17} aria-hidden="true" className="text-muted" />
          </button>
        ))}
      </div>
    </Card>
  )
}
