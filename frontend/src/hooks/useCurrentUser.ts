import { useQuery } from '@tanstack/react-query'

import { getMe } from '../lib/api'

export const CURRENT_USER_QUERY_KEY = ['me'] as const

export function useCurrentUser() {
  return useQuery({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: getMe,
    retry: false,
  })
}
