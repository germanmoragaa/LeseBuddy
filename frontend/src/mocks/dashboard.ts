// Placeholder data shaped like future API responses (see docs/blueprint.md section 6/10).
// Swap for TanStack Query calls once the backend endpoints exist — components should not
// need to change, only where this data comes from.

import type { DashboardStats, GoalProgress, StreakInfo } from '../types/dashboard'

export const mockStreak: StreakInfo = {
  days: 3,
  completedToday: [true, true, true, false, false, false, false],
}

export const mockDashboardStats: DashboardStats = {
  wordsLearned: 128,
  wordsLearnedDeltaThisWeek: 12,
  reviewsCompletedThisWeek: 34,
  readingHoursThisWeek: 2.4,
}

export const mockGoalProgress: GoalProgress = {
  minutesToday: 12,
  minutesGoal: 20,
}
