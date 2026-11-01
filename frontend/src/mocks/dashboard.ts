// Placeholder data shaped like future API responses (see docs/blueprint.md section 6/10).
// Swap for TanStack Query calls once the backend endpoints exist — components should not
// need to change, only where this data comes from.

import type { StreakInfo, UserSummary } from '../types/dashboard'

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
