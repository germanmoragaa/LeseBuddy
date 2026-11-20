import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleAnalysis, Token } from '../../types/analysis'
import { lineIndexByToken } from './lyricLines'
import { Reader } from './Reader'

// Invented lyric-style lines — never real copyrighted lyrics (see CLAUDE.md, ADR 0006).
const ARTICLE_ID = 'song-article-1'
const LYRICS = 'Erste Zeile hier\nZweite Zeile dort'

function makeToken(partial: Partial<Token> & Pick<Token, 'text' | 'start' | 'end'>): Token {
  return {
    whitespace_after: '',
    is_punct: false,
    is_space: false,
    lemma: partial.text,
    pos: 'X',
    morph: {},
    ...partial,
  }
}

const TOKENS: Token[] = [
  makeToken({ text: 'Erste', start: 0, end: 5, whitespace_after: ' ', pos: 'ADJ' }),
  makeToken({ text: 'Zeile', start: 6, end: 11, whitespace_after: ' ', pos: 'NOUN' }),
  makeToken({ text: 'hier', start: 12, end: 16, pos: 'ADV' }),
  makeToken({ text: '\n', start: 16, end: 17, is_space: true, pos: 'SPACE' }),
  makeToken({ text: 'Zweite', start: 17, end: 23, whitespace_after: ' ', pos: 'ADJ' }),
  makeToken({ text: 'Zeile', start: 24, end: 29, whitespace_after: ' ', pos: 'NOUN' }),
  makeToken({ text: 'dort', start: 30, end: 34, pos: 'ADV' }),
]

const ANALYSIS: ArticleAnalysis = {
  analysis_version: 1,
  difficulty_estimate: null,
  tokens: TOKENS,
  sentences: [{ start: 0, end: 34 }],
  separable_verbs: [],
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

interface MockOptions {
  selectionErrorCode?: string
}

function mockFetch(options: MockOptions = {}) {
  const article = {
    id: ARTICLE_ID,
    kind: 'song',
    title: 'Nachtlicht',
    source_url: null,
    language: 'de',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    original_text: LYRICS,
    reading_position: null,
    song: null,
  }
  const selectionError = options.selectionErrorCode
    ? jsonResponse(
        { detail: { code: options.selectionErrorCode, message: 'raw backend message' } },
        422,
      )
    : null

  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    if (path.endsWith('/analysis')) return Promise.resolve(jsonResponse(ANALYSIS))
    if (path.endsWith('/vocabulary-occurrences')) return Promise.resolve(jsonResponse([]))
    if (path.endsWith('/dictionary')) {
      if (selectionError) return Promise.resolve(selectionError.clone())
      return Promise.resolve(
        jsonResponse({
          lemma: 'Zeile',
          pos_detected: 'NOUN',
          is_separable_verb: false,
          entry: {
            pos: 'noun',
            gender: 'Fem',
            plural_only: false,
            plural: 'Zeilen',
            article: 'die',
            glosses: ['Reihe von Wörtern'],
            source_label: 'dictionary',
            translations: [
              { text: 'line', sense_label: 'Reihe' },
              { text: 'row', sense_label: 'Reihe' },
              { text: 'Line', sense_label: 'Text' },
            ],
          },
        }),
      )
    }
    if (path.endsWith('/translate')) {
      if (selectionError) return Promise.resolve(selectionError.clone())
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      return Promise.resolve(
        jsonResponse({
          selection_translation: 'line',
          sentence_translation: body.include_sentence ? 'First line here' : null,
          quota_warning: null,
          source: 'machine_translation',
        }),
      )
    }
    if (path === '/api/v1/decks') return Promise.resolve(jsonResponse({ items: [] }))
    if (path.endsWith('/open') || path.endsWith('/position') || path.endsWith(ARTICLE_ID)) {
      return Promise.resolve(jsonResponse(article))
    }
    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })
}

function renderReader() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/reader/${ARTICLE_ID}`]}>
        <Routes>
          <Route path="/app/reader/:articleId" element={<Reader />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('lineIndexByToken', () => {
  it('maps each token to the lyric line it starts on, by code point', () => {
    expect(lineIndexByToken(LYRICS, TOKENS)).toEqual([0, 0, 0, 0, 1, 1, 1])
  })

  it('counts code points, not UTF-16 units, before a newline', () => {
    const text = '🎵 Ja\nNein'
    const tokens = [
      makeToken({ text: 'Ja', start: 2, end: 4 }),
      makeToken({ text: 'Nein', start: 5, end: 9 }),
    ]
    expect(lineIndexByToken(text, tokens)).toEqual([0, 1])
  })
})

describe('Reader with a song', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('never builds a selection across two lyric lines, and says why', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByRole('button', { name: 'dort' })

    const [firstZeile] = screen.getAllByRole('button', { name: 'Zeile' })
    fireEvent.click(firstZeile)
    fireEvent.click(screen.getByRole('button', { name: 'dort' }), { shiftKey: true })

    // Snapped to the end of the anchor's line ("Zeile hier"), not across the newline.
    expect(await screen.findByText('Expression · offsets 6–16')).toBeInTheDocument()
    expect(screen.getByText('Selections stay within one line of the song.')).toBeInTheDocument()
  })

  it('shows the contextual translation "in this song" plus other dictionary meanings', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByRole('button', { name: 'dort' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Zeile' })[0])

    expect(await screen.findByText(/In this song/)).toBeInTheDocument()
    // "line"/"Line" are the contextual translation itself - only "row" is another meaning.
    expect(await screen.findByTestId('other-meanings')).toHaveTextContent('Other meanings: row')
    fireEvent.click(screen.getByRole('button', { name: /Translate line/ }))
    expect(await screen.findByText('First line here')).toBeInTheDocument()
  })

  it('shows a friendly message, never the raw error, when the API rejects the selection', async () => {
    vi.stubGlobal('fetch', mockFetch({ selectionErrorCode: 'selection_spans_lines' }))
    renderReader()
    await screen.findByRole('button', { name: 'dort' })

    fireEvent.click(screen.getByRole('button', { name: 'dort' }))

    expect(
      await screen.findByText('Pick words from a single line of the song.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('raw backend message')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Save to vocabulary/ })).toBeDisabled()
  })
})
