import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { FlashcardBack } from '../../types/flashcards'
import { CardBack } from './CardBack'

// Invented lyric-style line — never real copyrighted lyrics (see CLAUDE.md, ADR 0006).
const SONG_BACK: FlashcardBack = {
  meanings: [
    { text: 'bills', source: 'machine' },
    { text: 'shine', source: 'dictionary', sense_label: 'schwaches Leuchten' },
    { text: 'certificate', source: 'dictionary', sense_label: 'Bescheinigung' },
  ],
  example: {
    line: 'Die Scheine liegen auf dem Tisch',
    translation: 'The bills are lying on the table',
    highlight_start: 4,
    highlight_end: 11,
    song: {
      title: 'Nachtlicht',
      artist: 'Die Erfundenen',
      cover_url: 'https://images.genius.com/example-cover.jpg',
    },
  },
  translation: 'bills',
  glosses: ['schwaches Leuchten'],
  part_of_speech: 'NOUN',
  context_sentence: 'Die Scheine liegen auf dem Tisch',
}

describe('CardBack', () => {
  it('emphasizes the contextual meaning and lists the others in order', () => {
    render(<CardBack back={SONG_BACK} />)

    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('bills')
    expect(screen.getByText('In this context')).toBeInTheDocument()
    expect(screen.getByText(/shine, certificate/)).toBeInTheDocument()
  })

  it('shows the line with the word highlighted, its translation and the song', () => {
    const { container } = render(<CardBack back={SONG_BACK} />)

    expect(container.querySelector('mark')).toHaveTextContent('Scheine')
    expect(screen.getByText('The bills are lying on the table')).toBeInTheDocument()
    expect(screen.getByText('Nachtlicht')).toBeInTheDocument()
    expect(screen.getByText(/Die Erfundenen/)).toBeInTheDocument()
    expect(container.querySelector('img')).toHaveAttribute(
      'src',
      'https://images.genius.com/example-cover.jpg',
    )
  })

  it('highlights by code points, not UTF-16 units', () => {
    // "🎵" is one code point but two UTF-16 units: offsets 2..9 must still mark "Scheine".
    const back: FlashcardBack = {
      ...SONG_BACK,
      example: { ...SONG_BACK.example!, line: '🎵 Scheine im Licht', highlight_start: 2, highlight_end: 9 },
    }
    const { container } = render(<CardBack back={back} />)

    expect(container.querySelector('mark')).toHaveTextContent(/^Scheine$/)
  })

  it('has no song attribution for a text example', () => {
    const back: FlashcardBack = {
      ...SONG_BACK,
      example: { ...SONG_BACK.example!, song: null },
    }
    const { container } = render(<CardBack back={back} />)

    expect(container.querySelector('figcaption')).toBeNull()
  })

  it('falls back to the deprecated fields for legacy payloads', () => {
    const back: FlashcardBack = {
      meanings: [],
      example: null,
      translation: 'book',
      glosses: ['a bound collection of pages'],
      part_of_speech: 'NOUN',
      context_sentence: 'Das Buch liegt da.',
    }
    render(<CardBack back={back} />)

    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('book')
    expect(screen.getByText('Das Buch liegt da.')).toBeInTheDocument()
  })
})
