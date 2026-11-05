import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleListItem } from '../../types/article'
import { mockDashboardStats } from '../../mocks/dashboard'
import { Home } from './Home'

const TEST_USERNAME = 'alex_morgan'

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
  },
]

function meResponse() {
  return new Response(
    JSON.stringify({
      id: 'user-1',
      username: TEST_USERNAME,
      email: 'alex@example.com',
      email_verified: false,
      created_at: new Date().toISOString(),
    }),
    { status: 200 },
  )
}

function articlesResponse(items: ArticleListItem[]) {
  return new Response(
    JSON.stringify({ items, total: items.length, page: 1, page_size: items.length || 1 }),
    { status: 200 },
  )
}

function mockFetchWith(articles: ArticleListItem[]) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/me')) return Promise.resolve(meResponse())
    if (href.includes('/articles')) return Promise.resolve(articlesResponse(articles))
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderHome() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Home dashboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('greets the signed-in user by username', async () => {
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderHome()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(TEST_USERNAME)
    })
  })

  it('renders the dashboard stats from mock data', () => {
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderHome()

    expect(screen.getByText(String(mockDashboardStats.wordsLearned))).toBeInTheDocument()
    expect(screen.getByText(String(mockDashboardStats.reviewsCompletedThisWeek))).toBeInTheDocument()
    expect(screen.getByText(`${mockDashboardStats.readingHoursThisWeek}h`)).toBeInTheDocument()
  })

  it('renders the most recent real article as "pick up where you left off" and in recent reading', async () => {
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderHome()

    // The most recent article (article-2) legitimately appears twice: once in the
    // continue-reading card, once as the first row of the recent reading list.
    await waitFor(() => {
      expect(screen.getAllByText(ARTICLES[0].title!).length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.getByText(ARTICLES[1].title!)).toBeInTheDocument()
  })

  it('never renders a fabricated difficulty/level badge', async () => {
    vi.stubGlobal('fetch', mockFetchWith(ARTICLES))
    renderHome()

    await waitFor(() => {
      expect(screen.getAllByText(ARTICLES[0].title!).length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.queryByText(/B1|B2|Estimated/i)).not.toBeInTheDocument()
  })

  it('shows an empty state with a call to action when there are no articles', async () => {
    vi.stubGlobal('fetch', mockFetchWith([]))
    renderHome()

    await waitFor(() => {
      expect(screen.getAllByText(/haven't added any texts yet/i).length).toBeGreaterThan(0)
    })
    expect(screen.queryByText(/B1|B2|Estimated/i)).not.toBeInTheDocument()
  })
})
