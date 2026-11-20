import type { CoverSong } from '../../components/SongCover'
import { ApiError, isApiErrorDetail } from '../../lib/api'
import type { SongMetadata } from '../../types/article'
import type { SongSearchResult } from '../../types/song'

export function searchResultCover(song: SongSearchResult): CoverSong {
  return {
    title: song.title,
    primary_artist: song.primary_artist,
    cover_url: song.cover_url,
    cover_thumbnail_url: song.thumbnail_url,
  }
}

export function songSearchErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isApiErrorDetail(error.detail)) {
    if (error.detail.code === 'songs_not_configured') {
      return "Song search isn't set up yet. You can still paste your own text instead."
    }
    if (error.detail.code === 'songs_rate_limited') {
      return "You're searching very quickly. Wait a moment, then try again."
    }
  }
  return "Couldn't reach song search right now. Please try again in a moment."
}

export function releaseLabel(song: SongSearchResult): string | null {
  return song.release_year !== null ? String(song.release_year) : song.release_date_display
}

// "2021" from a full release date, or the first four-digit year in Genius' display string.
export function songYear(song: Pick<SongMetadata, 'release_date' | 'release_date_display'>) {
  if (song.release_date) return song.release_date.slice(0, 4)
  return song.release_date_display?.match(/\b\d{4}\b/)?.[0] ?? null
}

// "Die Erfundenen · 2021"
export function artistAndYear(song: SongMetadata): string {
  const year = songYear(song)
  return year ? `${song.primary_artist} · ${year}` : song.primary_artist
}
