import { Bookmark, Check, Clock, Layers } from 'lucide-react'
import { useNavigate } from 'react-router'

import { StatCard } from '../../components/StatCard'
import { mockDashboardStats } from '../../mocks/dashboard'
import { ContinueReadingCard } from './ContinueReadingCard'
import { GoalCard } from './GoalCard'
import { PracticeCard } from './PracticeCard'
import { RecentReadingList } from './RecentReadingList'
import { WelcomeBanner } from './WelcomeBanner'

export function Home() {
  const navigate = useNavigate()
  const stats = mockDashboardStats

  return (
    <div>
      <WelcomeBanner />

      <section className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Words learned"
          value={String(stats.wordsLearned)}
          detail={`+${stats.wordsLearnedDeltaThisWeek} this week`}
          icon={Bookmark}
          tone="mint"
          positive
        />
        <StatCard
          label="Reviews completed"
          value={String(stats.reviewsCompletedThisWeek)}
          detail="This week"
          icon={Check}
          tone="lavender"
        />
        <StatCard
          label="Due today"
          value={String(stats.dueToday)}
          detail="Ready when you are"
          icon={Layers}
          tone="yellow"
          action={{ label: 'Review now', onClick: () => navigate('/app/flashcards') }}
        />
        <StatCard
          label="Reading time"
          value={`${stats.readingHoursThisWeek}h`}
          detail="This week"
          icon={Clock}
          tone="coral"
        />
      </section>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.75fr)]">
        <ContinueReadingCard />
        <aside className="grid gap-4">
          <GoalCard />
          <PracticeCard />
        </aside>
      </div>

      <RecentReadingList />
    </div>
  )
}
