// Placeholder data shaped like future API responses (see docs/blueprint.md section 6/10).
// Swap for TanStack Query calls once the backend endpoints exist — components should not
// need to change, only where this data comes from.

import type {
  DashboardStats,
  GoalProgress,
  PracticeWord,
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

export const mockPracticeWords: PracticeWord[] = [
  { word: 'die Herausforderung', translation: 'challenge' },
  { word: 'sich gewöhnen an', translation: 'to get used to' },
  { word: 'auf jeden Fall', translation: 'definitely · in any case' },
]
