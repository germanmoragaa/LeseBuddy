import { BookOpen, Music } from 'lucide-react'
import { useState } from 'react'

// The minimal song shape a cover needs — saved songs, search results and flashcard
// attributions all map onto it.
export interface CoverSong {
  title: string
  primary_artist: string
  cover_url: string | null
  cover_thumbnail_url?: string | null
}

export type SongCoverSize = 'featured' | 'header' | 'list' | 'card'

const SIZES: Record<
  SongCoverSize,
  {
    px: number
    box: string
    initials: string
    icon: number
    preferThumbnail: boolean
  }
> = {
  featured: {
    px: 200,
    box: 'aspect-square w-full max-w-[200px] rounded-[12px]',
    initials: 'text-[44px]',
    icon: 22,
    preferThumbnail: false,
  },
  header: {
    px: 88,
    box: 'h-[88px] w-[88px] rounded-md',
    initials: 'text-[24px]',
    icon: 15,
    preferThumbnail: false,
  },
  list: {
    px: 40,
    box: 'h-10 w-10 rounded-sm',
    initials: 'text-[12px]',
    icon: 9,
    preferThumbnail: true,
  },
  card: {
    px: 28,
    box: 'h-7 w-7 rounded-[7px]',
    initials: 'text-[9px]',
    icon: 0,
    preferThumbnail: true,
  },
}

const FALLBACK_TONES = ['bg-surface-mint', 'bg-surface-lavender', 'bg-surface-coral'] as const

function songInitials(title: string): string {
  const words = title.match(/[\p{L}\p{N}]+/gu) ?? []
  return (
    words
      .slice(0, 2)
      .map((word) => word[0])
      .join('')
      .toLocaleUpperCase('de') || '♪'
  )
}

function fallbackTone(title: string) {
  let hash = 0
  for (const char of title) hash = (hash * 31 + char.codePointAt(0)!) | 0
  return FALLBACK_TONES[Math.abs(hash) % FALLBACK_TONES.length]
}

function coverUrl(song: CoverSong, preferThumbnail: boolean): string | null {
  const thumbnail = song.cover_thumbnail_url ?? null
  return preferThumbnail ? (thumbnail ?? song.cover_url) : (song.cover_url ?? thumbnail)
}

// "LESE PAUSE" tile for plain-text articles — their look predates song covers and stays.
function TextTile({ size }: { size: SongCoverSize }) {
  if (size === 'featured') {
    return (
      <div
        data-testid="text-cover"
        className="relative min-h-[150px] overflow-hidden rounded-[12px] bg-paper text-brand sm:min-h-[200px]"
        aria-hidden="true"
      >
        <span className="absolute left-[17px] top-[18px] text-[9px] font-extrabold tracking-widest">
          LESE
          <br />
          PAUSE
        </span>
      </div>
    )
  }
  return (
    <span
      data-testid="text-cover"
      className="grid h-9 w-8 shrink-0 place-items-center rounded-[5px_8px_8px_5px] bg-paper text-brand"
      aria-hidden="true"
    >
      <BookOpen size={18} />
    </span>
  )
}

function SongTile({ song, size }: { song: CoverSong; size: SongCoverSize }) {
  const { box, initials, icon } = SIZES[size]
  // Decorative: the title and artist are always shown right next to the cover.
  return (
    <span
      data-testid="song-cover-fallback"
      aria-hidden="true"
      className={`${box} ${fallbackTone(song.title)} relative grid shrink-0 place-items-center overflow-hidden text-brand`}
    >
      <span className={`${initials} font-extrabold leading-none tracking-tight`}>
        {songInitials(song.title)}
      </span>
      {icon > 0 && (
        <Music
          size={icon}
          className={
            size === 'list' ? 'absolute bottom-0.5 right-0.5' : 'absolute bottom-[8%] right-[8%]'
          }
        />
      )}
    </span>
  )
}

/**
 * A song's cover art, hotlinked from Genius and never copied to our server (ADR 0006). Falls
 * back to a designed tile when there's no cover or it fails to load; `song === null` means a
 * plain-text article, which keeps its "LESE PAUSE" look.
 */
export function SongCover({ song, size }: { song: CoverSong | null; size: SongCoverSize }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)

  if (song === null) return <TextTile size={size} />

  const { px, box, preferThumbnail } = SIZES[size]
  const url = coverUrl(song, preferThumbnail)
  if (url === null || url === failedUrl) return <SongTile song={song} size={size} />

  return (
    <img
      src={url}
      alt={`Cover of ${song.title} by ${song.primary_artist}`}
      width={px}
      height={px}
      loading="lazy"
      decoding="async"
      // Browsing must not tell Genius which page a user is on.
      referrerPolicy="no-referrer"
      onError={() => setFailedUrl(url)}
      className={`${box} shrink-0 bg-surface-lavender object-cover`}
    />
  )
}
