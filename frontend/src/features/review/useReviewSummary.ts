import { useQuery } from '@tanstack/react-query'

import { getReviewSummary } from '../../lib/api'

export function useReviewSummary(deckId?: string) {
  return useQuery({
    queryKey: ['reviews', 'summary', deckId ?? null],
    queryFn: () => getReviewSummary(deckId),
  })
}
