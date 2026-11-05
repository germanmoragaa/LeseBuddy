import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleListItem } from '../../types/article'
import { ReaderLibrary } from './ReaderLibrary'

const ARTICLE_FIRST: ArticleListItem = {
  id: 'article-first',
  title: 'First text',
  source_url: null,
  language: 'de',
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  word_count: 120,
  excerpt: 'Ein kurzer Auszug aus dem ersten Text...',
}

const ARTICLE_SECOND: ArticleListItem = {
  id: 'article-second',
  title: 'Second text',
  source_url: null,
  language: 'de',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  word_count: 400,
  excerpt: 'Ein Auszug aus dem zweiten Text...',
}

const ALL_ARTICLES = [ARTICLE_FIRST, ARTICLE_SECOND]

function jsonResponse(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), { status })
}

interface MockOptions {
  items?: ArticleListItem[]
  failList?: boolean
}

function mockFetch(options: MockOptions = {}) {
  const items = (options.items ?? ALL_ARTICLES).map((item) => ({ ...item }))

  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    const method = init?.method ?? 'GET'

    if (path === '/api/v1/articles' && method === 'GET') {
      if (options.failList) return Promise.resolve(jsonResponse({ detail: 'error' }, 500))
      const page = Number(url.searchParams.get('page') ?? '1')
      const pageSize = Number(url.searchParams.get('page_size') ?? '20')
      const start = (page - 1) * pageSize
      const pageItems = items.slice(start, start + pageSize)
      return Promise.resolve(
        jsonResponse({ items: pageItems, total: items.length, page, page_size: pageSize }),
      )
    }

    const detailMatch = path.match(/^\/api\/v1\/articles\/(.+)$/)
    if (detailMatch && method === 'PATCH') {
      const item = items.find((candidate) => candidate.id === detailMatch[1])
      if (!item) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      Object.assign(item, body)
      return Promise.resolve(jsonResponse(item))
    }

    if (detailMatch && method === 'DELETE') {
      const index = items.findIndex((candidate) => candidate.id === detailMatch[1])
      if (index !== -1) items.splice(index, 1)
      return Promise.resolve(jsonResponse(null, 204))
    }

    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })
}

function renderLibrary() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app/reader']}>
        <Routes>
          <Route path="/app/reader" element={<ReaderLibrary />} />
          <Route path="/app/reader/new" element={<div>Add text</div>} />
          <Route path="/app/reader/:articleId" element={<div>Article view</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReaderLibrary', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('lists the user\'s articles newest first with word count and read time', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderLibrary()

    expect(await screen.findByText('First text')).toBeInTheDocument()
    expect(screen.getByText('Second text')).toBeInTheDocument()
    expect(screen.getByText('120 words')).toBeInTheDocument()
    expect(screen.getByText('2 min read')).toBeInTheDocument()
  })

  it('shows an empty state with a call to action when there are no articles', async () => {
    vi.stubGlobal('fetch', mockFetch({ items: [] }))
    renderLibrary()

    expect(await screen.findByText(/haven't added any texts yet/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Add a text/ }).length).toBeGreaterThan(0)
  })

  it('shows an error state with a retry action', async () => {
    vi.stubGlobal('fetch', mockFetch({ failList: true }))
    renderLibrary()

    expect(await screen.findByText(/Couldn't load your reading library/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Try again/ })).toBeInTheDocument()
  })

  it('opens an article when its row is clicked', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderLibrary()
    await screen.findByText('First text')

    fireEvent.click(screen.getByText('First text'))

    expect(await screen.findByText('Article view')).toBeInTheDocument()
  })

  it('renames an article and persists the change', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderLibrary()
    await screen.findByText('First text')

    fireEvent.click(screen.getAllByRole('button', { name: 'Rename text' })[0])
    const input = screen.getByLabelText('Article title')
    fireEvent.change(input, { target: { value: 'Renamed text' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Renamed text')).toBeInTheDocument()
  })

  it('deletes an article after confirmation', async () => {
    vi.stubGlobal('fetch', mockFetch())
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderLibrary()
    await screen.findByText('First text')

    const deleteButtons = screen.getAllByRole('button', { name: 'Delete text' })
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.queryByText('First text')).not.toBeInTheDocument()
    })
  })

  it('does not delete when the confirmation is cancelled', async () => {
    vi.stubGlobal('fetch', mockFetch())
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderLibrary()
    await screen.findByText('First text')

    const deleteButtons = screen.getAllByRole('button', { name: 'Delete text' })
    fireEvent.click(deleteButtons[0])

    expect(screen.getByText('First text')).toBeInTheDocument()
  })

  it('paginates when there are more articles than fit on one page', async () => {
    const manyArticles = Array.from({ length: 25 }, (_, index) => ({
      ...ARTICLE_FIRST,
      id: `article-${index}`,
      title: `Text ${index}`,
    }))
    vi.stubGlobal('fetch', mockFetch({ items: manyArticles }))
    renderLibrary()

    expect(await screen.findByText('Text 0')).toBeInTheDocument()
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()
    expect(screen.queryByText('Text 20')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))

    expect(await screen.findByText('Text 20')).toBeInTheDocument()
  })

  it('never renders a difficulty/level badge', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderLibrary()
    await screen.findByText('First text')

    expect(screen.queryByText(/B1|B2|Estimated/i)).not.toBeInTheDocument()
  })
})
