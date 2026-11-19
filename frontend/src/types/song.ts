// Mirrors the backend's app/schemas/song.py (snake_case, matching the JSON the API returns).
// Metadata only — the app never fetches lyrics (docs/decisions/0006-songs-and-lyrics.md).

export interface SongSearchResult {
  genius_id: number
  title: string
  primary_artist: string
  thumbnail_url: string | null
  cover_url: string | null
  genius_url: string | null
  release_date_display: string | null
  release_year: number | null
  // ISO 639-1 code when Genius knows it ("de", "en", …); German results are ranked first.
  language: string | null
}

export interface SongSearchResponse {
  query: string
  results: SongSearchResult[]
}

export interface GeniusSong {
  genius_id: number
  title: string
  primary_artist: string
  album: string | null
  // ISO date (YYYY-MM-DD) when Genius has a full date; release_date_display otherwise.
  release_date: string | null
  release_date_display: string | null
  cover_url: string | null
  genius_url: string | null
  language: string | null
}

// POST /api/v1/songs — only the Genius id and the user's own pasted lyrics; the backend
// re-fetches every piece of metadata itself.
export interface SongCreatePayload {
  genius_song_id: number
  lyrics_text: string
}
