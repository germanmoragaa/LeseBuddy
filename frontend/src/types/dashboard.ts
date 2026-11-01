export interface UserSummary {
  name: string
  initials: string
  level: string
}

export interface StreakInfo {
  days: number
  completedToday: boolean[]
}
