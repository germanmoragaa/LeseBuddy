import { useQuery } from '@tanstack/react-query'

import { getReviewSummary } from '../../lib/api'

export function useReviewSummary() {
  return useQuery({
    queryKey: ['reviews', 'summary'],
    queryFn: getReviewSummary,
  })
}
