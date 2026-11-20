// Mirrors the backend's ArticleListItem/ArticleRead schemas (snake_case, matching the JSON
// the API returns).
export type ArticleKind = 'text' | 'song'

// Mirrors the backend's SongMetadataRead. Metadata comes from Genius' official API (or is
// typed in by hand for songs not on Genius); the lyrics themselves are the article's
// original_text, pasted by the user.
export interface SongMetadata {
  title: string
  primary_artist: string
  album: string | null
  // ISO date (YYYY-MM-DD) when known; Genius sometimes only has a display string instead.
  release_date: string | null
  release_date_display: string | null
  // Both hotlinked from Genius, never copied to our server (ADR 0006).
  cover_url: string | null
  cover_thumbnail_url: string | null
  genius_url: string | null
}

export interface ArticleListItem {
  id: string
  kind: ArticleKind
  title: string | null
  source_url: string | null
  language: string
  created_at: string
  updated_at: string
  word_count: number
  excerpt: string | null
  last_opened_at: string | null
  progress_percent: number | null
  // Null unless kind === 'song'.
  song: SongMetadata | null
}

export interface Article extends ArticleListItem {
  original_text: string
  reading_position: number | null
}

export interface ArticleCreatePayload {
  title?: string
  source_url?: string
  original_text: string
  language?: string
}

export interface ArticleUpdatePayload {
  title: string
}

export interface ArticleListResponse {
  items: ArticleListItem[]
  total: number
  page: number
  page_size: number
}
