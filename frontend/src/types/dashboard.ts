export interface StreakInfo {
  days: number
  completedToday: boolean[]
}

export interface DashboardStats {
  wordsLearned: number
  wordsLearnedDeltaThisWeek: number
  reviewsCompletedThisWeek: number
  readingHoursThisWeek: number
}

export interface GoalProgress {
  minutesToday: number
  minutesGoal: number
}
