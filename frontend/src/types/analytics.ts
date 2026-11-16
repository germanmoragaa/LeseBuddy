// Mirrors the backend's analytics schemas exactly (snake_case, matching the JSON the API
// returns). Every field here is a real, measured number - never a fabricated estimate.

export interface StreakInfo {
  current_days: number
  longest_days: number
  // Oldest to newest, always exactly 7 entries - the last one is today.
  last_7_days: boolean[]
}

export type RecommendationType = 'review' | 'continue_reading' | 'add_text'

export interface Recommendation {
  type: RecommendationType
  reason: string
  article_id: string | null
}

export interface AnalyticsOverview {
  words_saved: number
  words_mature: number
  words_saved_this_week: number
  reviews_today: number
  reviews_this_week: number
  due_now: number
  texts_opened_this_week: number
  streak: StreakInfo
  recommendation: Recommendation
}

export interface RatingCounts {
  again: number
  hard: number
  good: number
  easy: number
}

export interface RatingPercentages {
  again: number
  hard: number
  good: number
  easy: number
}

export interface DayActivity {
  date: string
  reviews: number
  words_saved: number
  cumulative_vocabulary: number
}

export interface AnalyticsActivity {
  days: DayActivity[]
  rating_counts: RatingCounts
  rating_percentages: RatingPercentages
  retention_percent: number | null
}

export type AnalyticsRangeDays = 7 | 30 | 90
