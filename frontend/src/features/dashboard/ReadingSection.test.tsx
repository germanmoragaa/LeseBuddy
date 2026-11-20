import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleListItem } from '../../types/article'
import { ReadingSection } from './ReadingSection'

const ARTICLES: ArticleListItem[] = [
  {
    id: 'article-2',
    title: 'Nachhaltiger leben im Alltag',
    source_url: null,
    language: 'de',
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    word_count: 240,
    excerpt: 'Wie wir im Alltag nachhaltiger leben können...',
    last_opened_at: '2026-01-05T00:00:00Z',
    progress_percent: 40,
    kind: 'text',
    song: null,
  },
  {
    id: 'article-1',
    title: 'Warum wir manchmal lieber zu Hause bleiben',
    source_url: null,
    language: 'de',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    word_count: 180,
    excerpt: 'Warum Zeit allein genau das sein kann, was wir brauchen.',
    last_opened_at: null,
    progress_percent: null,
    kind: 'text',
    song: null,
  },
]

// Invented song (ADR 0006): metadata only, an invented lyric-style excerpt.
const SONG_ARTICLE: ArticleListItem = {
  id: 'song-1',
  title: 'Nachtlicht',
  source_url: null,
  language: 'de',
  created_at: '2026-01-03T00:00:00Z',
  updated_at: '2026-01-03T00:00:00Z',
  word_count: 120,
  excerpt: "Ich lauf' durch die Nacht / Und die Stadt ist noch wach",
  last_opened_at: '2026-01-06T00:00:00Z',
  progress_percent: null,
  kind: 'song',
  song: {
    title: 'Nachtlicht',
    primary_artist: 'Die Erfundenen',
    album: 'Lieder aus Papier',
    release_date: '2021-05-14',
    release_date_display: 'May 14, 2021',
    cover_url: 'https://images.example.test/nachtlicht-1000x1000.jpg',
    cover_thumbnail_url: 'https://images.example.test/nachtlicht-300x300.jpg',
    genius_url: 'https://genius.example.test/die-erfundenen-nachtlicht',
  },
}

function articlesResponse(items: ArticleListItem[]) {
  return new Response(
    JSON.stringify({ items, total: items.length, page: 1, page_size: items.length || 1 }),
    { status: 200 },
  )
}

function mockFetchWith(items: ArticleListItem[] = []) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/articles')) return Promise.resolve(articlesResponse(items))
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderSection() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={<ReadingSection />} />
          <Route path="/app/reader" element={<div>Reading library</div>} />
          <Route path="/app/reader/new" element={<div>Add text</div>} />
          <Route path="/app/reader/:articleId" element={<div>Article view</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReadingSection', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests the recent sort order from the API', async () => {
    const fetchMock = mockFetchWith(ARTICLES)
    vi.stubGlobal('fetch', fetchMock)
    renderSection()

    await waitFor(() => {
      expect(screen.getByText(ARTICLES[0].title!)).toBeInTheDocument()
    })
    const requestedUrl = new URL(String(fetchMock.mock.calls[0][0]), 'http://localhost')
    expect(requestedUrl.searchParams.get('sort')).toBe('recent')
  })

  it('renders the most recent article as the featured card and the rest as a compact list', async () => {
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderSection()

    await waitFor(() => {
      expect(screen.getByText(ARTICLES[0].title!)).toBeInTheDocument()
    })
    expect(screen.getByText(ARTICLES[1].title!)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue reading/i })).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('orders the featured card from whatever the API returns first, not by created_at', async () => {
    // sort=recent means the API (not the client) decides order — the featured card must be
    // items[0] even though article-1 was created first.
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderSection()
    await waitFor(() => {
      expect(screen.getByText(ARTICLES[0].title!)).toBeInTheDocument()
    })

    expect(screen.getByText(/opened/i)).toBeInTheDocument()
    expect(screen.getByText(/added/i)).toBeInTheDocument()
  })

  it('shows an empty state with a call to action when there are no articles', async () => {
    vi.stubGlobal('fetch', mockFetchWith([]))
    renderSection()

    await waitFor(() => {
      expect(screen.getByText(/haven't added any texts yet/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /add a text/i })).toBeInTheDocument()
  })

  it('shows an error state with a retry action', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(null, { status: 500 }))))
    renderSection()

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load/i)
    })
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('shows song covers with artist and year, and keeps the text tile for texts', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchWith([
        SONG_ARTICLE,
        ARTICLES[0],
        {
          ...SONG_ARTICLE,
          id: 'song-2',
          title: 'Zweites Lied',
          song: { ...SONG_ARTICLE.song!, title: 'Zweites Lied' },
        },
      ]),
    )
    renderSection()

    const featuredCover = await screen.findByRole('img', {
      name: 'Cover of Nachtlicht by Die Erfundenen',
    })
    expect(featuredCover).toHaveAttribute('src', SONG_ARTICLE.song!.cover_url)
    expect(screen.getAllByText('Die Erfundenen · 2021')).toHaveLength(2)
    expect(screen.queryByText('LESE')).not.toBeInTheDocument()
    // The compact list: the second song uses the thumbnail, the text keeps its book tile.
    const thumbnails = screen
      .getAllByRole('img')
      .filter((img) => img.getAttribute('src') === SONG_ARTICLE.song!.cover_thumbnail_url)
    expect(thumbnails).toHaveLength(1)
    expect(screen.getByTestId('text-cover')).toBeInTheDocument()
  })
})
