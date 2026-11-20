import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { type CoverSong, SongCover } from './SongCover'

// Invented song (ADR 0006: never real lyrics or songs in tests).
const SONG: CoverSong = {
  title: 'Nachtlicht am Fluss',
  primary_artist: 'Die Erfundenen',
  cover_url: 'https://images.example.test/nachtlicht-1000x1000.jpg',
  cover_thumbnail_url: 'https://images.example.test/nachtlicht-300x300.jpg',
}

describe('SongCover', () => {
  it('renders the hotlinked cover with layout-stable, privacy-safe attributes', () => {
    render(<SongCover song={SONG} size="featured" />)

    const img = screen.getByRole('img', {
      name: 'Cover of Nachtlicht am Fluss by Die Erfundenen',
    })
    expect(img).toHaveAttribute('src', SONG.cover_url)
    expect(img).toHaveAttribute('loading', 'lazy')
    expect(img).toHaveAttribute('decoding', 'async')
    expect(img).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(img).toHaveAttribute('width', '200')
    expect(img).toHaveAttribute('height', '200')
  })

  it('uses the thumbnail for small sizes and the full cover for large ones', () => {
    const { rerender } = render(<SongCover song={SONG} size="list" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', SONG.cover_thumbnail_url)

    rerender(<SongCover song={SONG} size="header" />)
    expect(screen.getByRole('img')).toHaveAttribute('src', SONG.cover_url)
  })

  it('falls back to the other URL when only one is known', () => {
    render(<SongCover song={{ ...SONG, cover_thumbnail_url: null }} size="card" />)

    expect(screen.getByRole('img')).toHaveAttribute('src', SONG.cover_url)
  })

  it('shows the designed song tile with initials when the image fails to load', () => {
    render(<SongCover song={SONG} size="header" />)

    fireEvent.error(screen.getByRole('img'))

    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    const tile = screen.getByTestId('song-cover-fallback')
    expect(tile).toHaveTextContent('NA')
    expect(tile.querySelector('svg')).not.toBeNull()
  })

  it('shows the song tile when there is no cover at all', () => {
    render(
      <SongCover
        song={{
          ...SONG,
          title: 'über alles',
          cover_url: null,
          cover_thumbnail_url: null,
        }}
        size="list"
      />,
    )

    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByTestId('song-cover-fallback')).toHaveTextContent('ÜA')
  })

  it('keeps the "LESE PAUSE" tile for text articles', () => {
    const { rerender } = render(<SongCover song={null} size="featured" />)

    expect(screen.getByTestId('text-cover')).toHaveTextContent('LESEPAUSE')
    expect(screen.queryByRole('img')).not.toBeInTheDocument()

    rerender(<SongCover song={null} size="list" />)
    expect(screen.getByTestId('text-cover')).not.toHaveTextContent('LESE')
    expect(screen.queryByTestId('song-cover-fallback')).not.toBeInTheDocument()
  })
})
