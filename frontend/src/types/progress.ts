export type TimeRange = '7 days' | '30 days' | 'All time'

export interface StudyActivityPoint {
  dayLabel: string
  heightPercent: number
  count: number
}

export interface ReviewResponseBreakdown {
  again: number
  hard: number
  good: number
  easy: number
}

export interface ProgressOverview {
  vocabularySaved: number
  vocabularySavedDeltaThisWeek: number
  reviewsCompleted: number
  reviewsCompletedDeltaThisWeek: number
  readingHours: number
  readingHoursDeltaThisWeek: number
  currentStreakDays: number
  personalBestStreakDays: number
  vocabularyGrowthDelta: number
  totalReviewsForBreakdown: number
}
