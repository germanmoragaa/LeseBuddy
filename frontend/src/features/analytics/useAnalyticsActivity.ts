import { useQuery } from '@tanstack/react-query'

import { getAnalyticsActivity } from '../../lib/api'
import type { AnalyticsRangeDays } from '../../types/analytics'

export function useAnalyticsActivity(days: AnalyticsRangeDays = 7) {
  return useQuery({
    queryKey: ['analytics', 'activity', days],
    queryFn: () => getAnalyticsActivity(days),
  })
}
