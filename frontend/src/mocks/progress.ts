// Placeholder data shaped like future API responses (see docs/blueprint.md section 10).
// Swap for GET /api/v1/analytics/* calls once those endpoints exist.

import type { ProgressOverview, ReviewResponseBreakdown, StudyActivityPoint } from '../types/progress'

export const mockProgressOverview: ProgressOverview = {
  vocabularySaved: 128,
  vocabularySavedDeltaThisWeek: 12,
  reviewsCompleted: 246,
  reviewsCompletedDeltaThisWeek: 34,
  readingHours: 6.5,
  readingHoursDeltaThisWeek: 2.4,
  currentStreakDays: 3,
  personalBestStreakDays: 11,
  vocabularyGrowthDelta: 23,
  totalReviewsForBreakdown: 34,
}

const dayLabels = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const sevenDayValues = [38, 58, 24, 75, 52, 92, 66]

export const mockStudyActivity: StudyActivityPoint[] = sevenDayValues.map((value, index) => ({
  dayLabel: dayLabels[index],
  heightPercent: value,
  count: Math.round(value / 8),
}))

export const mockReviewResponseBreakdown: ReviewResponseBreakdown = {
  again: 9,
  hard: 18,
  good: 56,
  easy: 17,
}
