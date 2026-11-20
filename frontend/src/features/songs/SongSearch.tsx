import { Loader2, Music, Search } from 'lucide-react'
import { useId, useState } from 'react'

import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import type { SongSearchResult } from '../../types/song'
import { AddSongDialog } from './AddSongDialog'
import { SongCover } from '../../components/SongCover'
import { releaseLabel, searchResultCover, songSearchErrorMessage } from './songFormat'
import { SONG_SEARCH_DEBOUNCE_MS, SONG_SEARCH_MIN_LENGTH, useSongSearch } from './useSongSearch'

// Inline variant of the header's song search, for the "New reading" screen: pick a result
// and AddSongDialog takes over (paste lyrics -> save -> open in the reader).
export function SongSearch() {
  const inputId = useId()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<SongSearchResult | null>(null)
  const debouncedQuery = useDebouncedValue(query, SONG_SEARCH_DEBOUNCE_MS)
  const search = useSongSearch(debouncedQuery)

  const trimmed = debouncedQuery.trim()
  const isActive = trimmed.length >= SONG_SEARCH_MIN_LENGTH
  const results = search.data?.results ?? []

  return (
    <section aria-labelledby={`${inputId}-heading`} className="text-left">
      <h2 id={`${inputId}-heading`} className="mb-1.5 flex items-center gap-1.5 text-[13px] font-bold">
        <Music size={15} aria-hidden="true" className="text-brand" /> Find a song
      </h2>
      <label htmlFor={inputId} className="mb-1.5 block text-[10px] text-muted">
        Search by title or artist. We only look up the song's details; you'll add the lyrics
        yourself.
      </label>
      <div className="relative">
        <Search
          size={15}
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-muted"
        />
        <input
          id={inputId}
          type="search"
          value={query}
          maxLength={100}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="e.g. a song title or artist"
          autoComplete="off"
          className="h-[43px] w-full rounded-sm border border-line pr-9 pl-9 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
        />
        {isActive && search.isFetching && (
          <Loader2
            size={15}
            aria-hidden="true"
            className="absolute top-1/2 right-3.5 -translate-y-1/2 animate-spin text-muted"
          />
        )}
      </div>

      <div aria-live="polite" className="mt-2">
        {!isActive ? null : search.isError ? (
          <p role="alert" className="rounded-sm bg-surface-coral px-3.5 py-2.5 text-[10px] text-danger">
            {songSearchErrorMessage(search.error)}
          </p>
        ) : search.isPending ? (
          <p className="text-[10px] text-muted">Searching…</p>
        ) : results.length === 0 ? (
          <p className="text-[10px] text-muted">No songs found for “{trimmed}”.</p>
        ) : (
          <ul
            aria-label="Song results"
            className={`grid max-h-[260px] gap-1 overflow-y-auto rounded-sm border border-line p-1 transition-opacity ${
              search.isPlaceholderData ? 'opacity-60' : ''
            }`}
          >
            {results.map((song) => {
              const release = releaseLabel(song)
              return (
                <li key={song.genius_id}>
                  <button
                    type="button"
                    onClick={() => setSelected(song)}
                    className="flex w-full items-center gap-3 rounded-sm px-2 py-1.5 text-left hover:bg-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
                  >
                    <SongCover song={searchResultCover(song)} size="list" />
                    <span className="min-w-0">
                      <span className="block truncate text-[11px] font-bold text-ink">
                        {song.title}
                      </span>
                      <span className="block truncate text-[10px] text-muted">
                        {song.primary_artist}
                        {release ? ` · ${release}` : ''}
                      </span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      {selected && <AddSongDialog song={selected} onClose={() => setSelected(null)} />}
    </section>
  )
}
