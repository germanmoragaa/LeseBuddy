import { Loader2, Search } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import type { SongSearchResult } from '../../types/song'
import { AddSongDialog } from './AddSongDialog'
import { SongCover } from './SongCover'
import { releaseLabel, songSearchErrorMessage } from './songFormat'
import { SONG_SEARCH_DEBOUNCE_MS, SONG_SEARCH_MIN_LENGTH, useSongSearch } from './useSongSearch'

// The app-wide header search: find a song on Genius (metadata only), pick it, paste the
// lyrics in AddSongDialog, and it's saved straight into the user's library.
export function HeaderSongSearch() {
  const listboxId = useId()
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [selected, setSelected] = useState<SongSearchResult | null>(null)
  const debouncedQuery = useDebouncedValue(query, SONG_SEARCH_DEBOUNCE_MS)
  const search = useSongSearch(debouncedQuery)

  const trimmed = debouncedQuery.trim()
  const isActive = trimmed.length >= SONG_SEARCH_MIN_LENGTH
  const results = isActive && !search.isError ? (search.data?.results ?? []) : []
  const showDropdown = isOpen && isActive
  // Results can shrink when a newer search lands; never point past the end of the list.
  const highlighted = activeIndex < results.length ? activeIndex : -1

  useEffect(() => {
    if (!isOpen) return
    const onMouseDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [isOpen])

  function choose(song: SongSearchResult) {
    setSelected(song)
    setIsOpen(false)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setIsOpen(false)
      return
    }
    if (!showDropdown || results.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((highlighted + 1) % results.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex(highlighted <= 0 ? results.length - 1 : highlighted - 1)
    } else if (event.key === 'Enter' && highlighted >= 0) {
      event.preventDefault()
      choose(results[highlighted])
    }
  }

  return (
    <div ref={containerRef} className="relative hidden sm:block">
      <label className="flex h-[38px] items-center gap-2 rounded-sm border border-line bg-white px-2.5 text-muted has-[input:focus-visible]:outline has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-action">
        <Search size={17} aria-hidden="true" />
        <input
          ref={inputRef}
          type="search"
          role="combobox"
          aria-label="Search songs"
          aria-expanded={showDropdown}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            showDropdown && highlighted >= 0 ? `${listboxId}-${highlighted}` : undefined
          }
          autoComplete="off"
          maxLength={100}
          value={query}
          placeholder="Search songs to add…"
          onChange={(event) => {
            setQuery(event.target.value)
            setActiveIndex(-1)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={onKeyDown}
          className="w-[200px] border-0 bg-transparent text-xs text-ink outline-none"
        />
        {isActive && search.isFetching && (
          <Loader2 size={14} aria-hidden="true" className="animate-spin" />
        )}
      </label>

      {showDropdown && (
        <div className="absolute top-[calc(100%+6px)] right-0 z-30 w-[340px] rounded-md border border-line bg-white p-1.5 shadow-card">
          {search.isError ? (
            <p role="alert" className="px-2.5 py-2 text-[11px] text-danger">
              {songSearchErrorMessage(search.error)}
            </p>
          ) : search.isPending ? (
            <p className="px-2.5 py-2 text-[11px] text-muted">Searching…</p>
          ) : results.length === 0 ? (
            <p className="px-2.5 py-2 text-[11px] text-muted">No songs found for “{trimmed}”.</p>
          ) : (
            <ul
              id={listboxId}
              role="listbox"
              aria-label="Song results"
              className={`grid max-h-[340px] gap-0.5 overflow-y-auto ${
                search.isPlaceholderData ? 'opacity-60' : ''
              }`}
            >
              {results.map((song, index) => {
                const release = releaseLabel(song)
                return (
                  <li
                    key={song.genius_id}
                    id={`${listboxId}-${index}`}
                    role="option"
                    aria-selected={index === highlighted}
                    onClick={() => choose(song)}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={`flex cursor-pointer items-center gap-3 rounded-sm px-2 py-1.5 ${
                      index === highlighted ? 'bg-surface-mint' : ''
                    }`}
                  >
                    <SongCover url={song.thumbnail_url} size="sm" />
                    <span className="min-w-0">
                      <span className="block truncate text-[12px] font-bold text-ink">
                        {song.title}
                      </span>
                      <span className="block truncate text-[10px] text-muted">
                        {song.primary_artist}
                        {release ? ` · ${release}` : ''}
                      </span>
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
          <p className="border-t border-line px-2.5 pt-1.5 pb-0.5 text-[9px] text-muted">
            Song details from Genius. You'll paste the lyrics yourself.
          </p>
        </div>
      )}

      {selected && (
        <AddSongDialog
          song={selected}
          onClose={() => {
            setSelected(null)
            inputRef.current?.focus()
          }}
        />
      )}
    </div>
  )
}
