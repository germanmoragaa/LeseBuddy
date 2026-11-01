export interface UserSummary {
  name: string
  initials: string
  level: string
}

export interface StreakInfo {
  days: number
  completedToday: boolean[]
}

export interface DashboardStats {
  wordsLearned: number
  wordsLearnedDeltaThisWeek: number
  reviewsCompletedThisWeek: number
  dueToday: number
  readingHoursThisWeek: number
}

export interface GoalProgress {
  minutesToday: number
  minutesGoal: number
}

export interface ContinueReadingArticle {
  id: string
  title: string
  description: string
  estimatedLevel: string
  readMinutes: number
  percentComplete: number
}

export interface PracticeWord {
  word: string
  translation: string
}

export interface RecentArticle {
  id: string
  title: string
  category: string
  level: string
  percentComplete: number
  lastOpenedLabel: string
}
