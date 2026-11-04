import { ArrowRight, BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Badge } from '../../components/Badge'
import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { ProgressBar } from '../../components/ProgressBar'
import { mockContinueReading } from '../../mocks/dashboard'

export function ContinueReadingCard() {
  const navigate = useNavigate()
  const article = mockContinueReading

  return (
    <Card className="p-5.5">
      <div className="flex items-center gap-2 text-xs font-bold">
        <span className="grid h-[29px] w-[29px] place-items-center rounded-[8px] bg-surface-mint text-brand">
          <BookOpen size={17} aria-hidden="true" />
        </span>
        Pick up where you left off
      </div>
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
            <Badge>{article.estimatedLevel}</Badge>
            <Badge tone="plain">{article.readMinutes} min read</Badge>
          </div>
          <h2 className="my-3 max-w-[460px] text-[clamp(19px,2vw,25px)] leading-tight tracking-tight">
            {article.title}
          </h2>
          <p className="mb-5 text-xs text-muted">{article.description}</p>
          <div className="mb-1.5 flex justify-between text-[10px] text-muted">
            <span>
              <strong className="text-ink">{article.percentComplete}%</strong> read
            </span>
            <span>Last opened today</span>
          </div>
          <ProgressBar value={article.percentComplete} />
          <Button className="mt-5" onClick={() => navigate('/app/reader/new')}>
            Continue reading <ArrowRight size={17} aria-hidden="true" />
          </Button>
        </div>
      </div>
    </Card>
  )
}
