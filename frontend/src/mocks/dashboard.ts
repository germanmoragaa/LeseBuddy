// Placeholder data shaped like future API responses (see docs/blueprint.md section 6/10).
// Swap for TanStack Query calls once the backend endpoints exist — components should not
// need to change, only where this data comes from.

import type {
  ContinueReadingArticle,
  DashboardStats,
  GoalProgress,
  PracticeWord,
  RecentArticle,
  StreakInfo,
  UserSummary,
} from '../types/dashboard'

export const mockUser: UserSummary = {
  name: 'Alex Morgan',
  initials: 'AM',
  level: 'German learner · B1',
}

export const mockStreak: StreakInfo = {
  days: 3,
  completedToday: [true, true, true, false, false, false, false],
}

export const mockDueFlashcardsCount = 8

export const mockDashboardStats: DashboardStats = {
  wordsLearned: 128,
  wordsLearnedDeltaThisWeek: 12,
  reviewsCompletedThisWeek: 34,
  dueToday: mockDueFlashcardsCount,
  readingHoursThisWeek: 2.4,
}

export const mockGoalProgress: GoalProgress = {
  minutesToday: 12,
  minutesGoal: 20,
}

export const mockContinueReading: ContinueReadingArticle = {
  id: 'warum-zu-hause-bleiben',
  title: 'Warum wir manchmal lieber zu Hause bleiben',
  description: 'Why spending time alone can be exactly what we need.',
  estimatedLevel: 'B1–B2 · Estimated',
  readMinutes: 12,
  percentComplete: 68,
}

export const mockPracticeWords: PracticeWord[] = [
  { word: 'die Herausforderung', translation: 'challenge' },
  { word: 'sich gewöhnen an', translation: 'to get used to' },
  { word: 'auf jeden Fall', translation: 'definitely · in any case' },
]

export const mockRecentArticles: RecentArticle[] = [
  {
    id: 'warum-zu-hause-bleiben',
    title: 'Warum wir manchmal lieber zu Hause bleiben',
    category: 'Mind & everyday life',
    level: 'B1–B2',
    percentComplete: 68,
    lastOpenedLabel: 'Today',
  },
  {
    id: 'nachhaltiger-leben',
    title: 'Nachhaltiger leben im Alltag',
    category: 'Environment',
    level: 'B1',
    percentComplete: 32,
    lastOpenedLabel: 'Yesterday',
  },
  {
    id: 'arbeiten-von-ueberall',
    title: 'Arbeiten von überall: Fluch oder Segen?',
    category: 'Work & culture',
    level: 'B2',
    percentComplete: 100,
    lastOpenedLabel: 'May 18',
  },
]
