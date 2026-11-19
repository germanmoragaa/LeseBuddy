import { Music } from 'lucide-react'

const COVER_SIZES = {
  sm: { box: 'h-10 w-10', icon: 16 },
  md: { box: 'h-12 w-12', icon: 18 },
  lg: { box: 'h-16 w-16', icon: 22 },
} as const

export function SongCover({ url, size }: { url: string | null; size: keyof typeof COVER_SIZES }) {
  const { box, icon } = COVER_SIZES[size]
  if (!url) {
    return (
      <span
        className={`${box} grid shrink-0 place-items-center rounded-sm bg-surface-lavender text-muted`}
      >
        <Music size={icon} aria-hidden="true" />
      </span>
    )
  }
  // Hotlinked from Genius, never copied to our server (ADR 0006); no-referrer so browsing
  // doesn't leak which page a user is on. alt="" because the title is always right next to it.
  return (
    <img
      src={url}
      alt=""
      loading="lazy"
      referrerPolicy="no-referrer"
      className={`${box} shrink-0 rounded-sm bg-surface-lavender object-cover`}
    />
  )
}
