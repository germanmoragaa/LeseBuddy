import { useQuery } from '@tanstack/react-query'

import { getDueCards } from '../../lib/api'

export function useDueCards(limit = 20, deckId?: string) {
  return useQuery({
    queryKey: ['reviews', 'due', limit, deckId ?? null],
    queryFn: () => getDueCards(limit, deckId),
  })
}
