import { useQuery } from '@tanstack/react-query'

import { listArticles } from '../../lib/api'

const RECENT_SECTION_COUNT = 5

// Shared by WelcomeBanner's hero CTA and ReadingSection so both read the exact same
// most-recent article — same queryKey means TanStack Query also dedupes the two call
// sites into a single request.
export function useRecentArticles() {
  return useQuery({
    queryKey: ['articles', 'recent-section'],
    queryFn: () => listArticles({ page: 1, pageSize: RECENT_SECTION_COUNT, sort: 'recent' }),
  })
}
