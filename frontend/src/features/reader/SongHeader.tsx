import { ExternalLink } from 'lucide-react'

import { SongCover } from '../../components/SongCover'
import type { SongMetadata } from '../../types/article'
import { songYear } from '../songs/songFormat'

// Reader title block for a song: cover, title, artist, album/year and a link to its Genius
// page (ADR 0006: every song links back to Genius).
export function SongHeader({ title, song }: { title: string | null; song: SongMetadata }) {
  const details = [song.album, songYear(song)].filter(Boolean).join(' · ')

  return (
    <div className="my-3 flex items-center gap-5">
      <SongCover song={song} size="header" />
      <div className="min-w-0">
        <h1 className="m-0 max-w-[600px] text-[clamp(26px,3vw,38px)] leading-tight tracking-tight">
          {title ?? song.title}
        </h1>
        <p className="m-0 mt-1 text-[14px] font-semibold text-ink">{song.primary_artist}</p>
        {details && <p className="m-0 mt-0.5 text-[12px] text-muted">{details}</p>}
        {song.genius_url && (
          <a
            href={song.genius_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-bold text-action hover:underline"
          >
            View on Genius <ExternalLink size={12} aria-hidden="true" />
          </a>
        )}
      </div>
    </div>
  )
}
