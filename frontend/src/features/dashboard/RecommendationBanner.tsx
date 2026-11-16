import { ArrowRight, BookOpen, Layers, Plus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import type { Recommendation } from '../../types/analytics'

const ACTION_BY_TYPE: Record<Recommendation['type'], { label: string; icon: LucideIcon }> = {
  review: { label: 'Review now', icon: Layers },
  continue_reading: { label: 'Continue reading', icon: BookOpen },
  add_text: { label: 'Add a text', icon: Plus },
}

interface RecommendationBannerProps {
  recommendation: Recommendation
}

export function RecommendationBanner({ recommendation }: RecommendationBannerProps) {
  const navigate = useNavigate()
  const { label, icon: Icon } = ACTION_BY_TYPE[recommendation.type]

  function handleClick() {
    if (recommendation.type === 'review') {
      navigate('/app/flashcards')
    } else if (recommendation.type === 'continue_reading' && recommendation.article_id) {
      navigate(`/app/reader/${recommendation.article_id}`)
    } else {
      navigate('/app/reader/new')
    }
  }

  return (
    <section className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-white px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-surface-mint text-brand">
          <Icon size={18} aria-hidden="true" />
        </span>
        <p className="m-0 text-[13px]">{recommendation.reason}</p>
      </div>
      <Button onClick={handleClick}>
        {label} <ArrowRight size={16} aria-hidden="true" />
      </Button>
    </section>
  )
}
