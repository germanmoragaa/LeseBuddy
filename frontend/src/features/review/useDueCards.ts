import { useQuery } from '@tanstack/react-query'

import { getDueCards } from '../../lib/api'

export function useDueCards(limit = 20) {
  return useQuery({
    queryKey: ['reviews', 'due', limit],
    queryFn: () => getDueCards(limit),
  })
}
