import { BookOpen, Bookmark, Check, Sparkles } from 'lucide-react'

import { StatCard } from '../../components/StatCard'
import { useAnalyticsOverview } from '../analytics/useAnalyticsOverview'
import { PracticeCard } from './PracticeCard'
import { ReadingSection } from './ReadingSection'
import { RecommendationBanner } from './RecommendationBanner'
import { TodayCard } from './TodayCard'
import { WelcomeBanner } from './WelcomeBanner'

export function Home() {
  const { data: overview } = useAnalyticsOverview()

  return (
    <div>
      <WelcomeBanner />

      <section className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Words saved"
          value={overview ? String(overview.words_saved) : '—'}
          detail={overview ? `+${overview.words_saved_this_week} this week` : ''}
          icon={Bookmark}
          tone="mint"
          positive
        />
        <StatCard
          label="Mature words"
          value={overview ? String(overview.words_mature) : '—'}
          detail="Interval 21+ days"
          icon={Sparkles}
          tone="lavender"
        />
        <StatCard
          label="Reviews this week"
          value={overview ? String(overview.reviews_this_week) : '—'}
          detail="This week"
          icon={Check}
          tone="yellow"
        />
        <StatCard
          label="Texts opened"
          value={overview ? String(overview.texts_opened_this_week) : '—'}
          detail="This week"
          icon={BookOpen}
          tone="coral"
        />
      </section>

      {overview && <RecommendationBanner recommendation={overview.recommendation} />}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.75fr)]">
        <ReadingSection />
        <aside className="grid gap-4">
          <TodayCard />
          <PracticeCard />
        </aside>
      </div>
    </div>
  )
}
