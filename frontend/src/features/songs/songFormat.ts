import { ApiError, isApiErrorDetail } from '../../lib/api'
import type { SongSearchResult } from '../../types/song'

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
