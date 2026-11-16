import { useQuery } from '@tanstack/react-query'

import { getAnalyticsOverview } from '../../lib/api'

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: getAnalyticsOverview,
  })
}
