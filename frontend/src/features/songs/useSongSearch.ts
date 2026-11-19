import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { searchSongs } from '../../lib/api'

export const SONG_SEARCH_MIN_LENGTH = 2
export const SONG_SEARCH_DEBOUNCE_MS = 300

// `query` should already be debounced by the caller. Keeps the previous results on screen
// while the next query loads, so the list doesn't flash empty on every keystroke pause.
export function useSongSearch(query: string) {
  const trimmed = query.trim()
  return useQuery({
    queryKey: ['songs', 'search', trimmed],
    queryFn: () => searchSongs(trimmed),
    enabled: trimmed.length >= SONG_SEARCH_MIN_LENGTH,
    placeholderData: keepPreviousData,
    // Results barely change; the backend caches them for 10 minutes too.
    staleTime: 5 * 60_000,
    // Not-configured (503), rate-limited (429) and provider errors won't fix themselves
    // within a retry's backoff; the next keystroke pause is the natural retry.
    retry: false,
  })
}
