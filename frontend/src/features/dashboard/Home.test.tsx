import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsOverview } from '../../types/analytics'
import type { ArticleListItem } from '../../types/article'
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

const OVERVIEW: AnalyticsOverview = {
  words_saved: 128,
  words_mature: 42,
  words_saved_this_week: 12,
  reviews_today: 3,
  reviews_this_week: 34,
  due_now: 7,
  texts_opened_this_week: 2,
  streak: { current_days: 3, longest_days: 11, last_7_days: [true, true, true, false, false, false, false] },
  recommendation: { type: 'review', reason: 'You have 7 cards due', article_id: null },
}

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

interface MockOptions {
  articles?: ArticleListItem[]
  dueCount?: number
  overview?: AnalyticsOverview
}

function mockFetchWith({ articles = [], dueCount = 0, overview = OVERVIEW }: MockOptions = {}) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/me')) return Promise.resolve(meResponse())
    if (href.includes('/articles')) return Promise.resolve(articlesResponse(articles))
    if (href.includes('/analytics/overview')) {
      return Promise.resolve(new Response(JSON.stringify(overview), { status: 200 }))
    }
    if (href.includes('/reviews/due')) {
      return Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }))
    }
    if (href.includes('/reviews/summary')) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ due_count: dueCount, next_due_at: null, total_cards: dueCount }),
          { status: 200 },
        ),
      )
    }
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderHome() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={<Home />} />
          <Route path="/app/reader" element={<div>Reading library</div>} />
          <Route path="/app/reader/new" element={<div>Add text</div>} />
          <Route path="/app/reader/:articleId" element={<div>Article view</div>} />
          <Route path="/app/flashcards" element={<div>Flashcards</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Home dashboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('greets the signed-in user by username', async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES }))
    renderHome()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(TEST_USERNAME)
    })
  })

  it('renders the real analytics stats', async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES }))
    renderHome()

    expect(await screen.findByText(String(OVERVIEW.words_saved))).toBeInTheDocument()
    expect(screen.getByText(`+${OVERVIEW.words_saved_this_week} this week`)).toBeInTheDocument()
    expect(screen.getByText(String(OVERVIEW.words_mature))).toBeInTheDocument()
    expect(screen.getByText(String(OVERVIEW.reviews_this_week))).toBeInTheDocument()
    expect(screen.getByText(String(OVERVIEW.texts_opened_this_week))).toBeInTheDocument()
  })

  it('shows the recommendation reason and routes its action button', async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES }))
    renderHome()

    expect(await screen.findByText(OVERVIEW.recommendation.reason)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /review now/i }))

    expect(await screen.findByText('Flashcards')).toBeInTheDocument()
  })

  it('recommends continuing an unfinished article when nothing is due', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchWith({
        articles: ARTICLES,
        overview: {
          ...OVERVIEW,
          due_now: 0,
          recommendation: {
            type: 'continue_reading',
            reason: 'Pick up where you left off',
            article_id: 'article-2',
          },
        },
      }),
    )
    renderHome()

    // "Continue reading" is ambiguous on this page (the hero banner and the reading section
    // both say it too) - scope to the recommendation banner itself via its reason text.
    const reasonText = await screen.findByText('Pick up where you left off')
    const banner = reasonText.closest('section')
    expect(banner).not.toBeNull()
    fireEvent.click(within(banner!).getByRole('button', { name: /continue reading/i }))

    expect(await screen.findByText('Article view')).toBeInTheDocument()
  })

  it('renders the most recent article as the featured card and the rest in the list below', async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES }))
    renderHome()

    await waitFor(() => {
      expect(screen.getByText(ARTICLES[0].title!)).toBeInTheDocument()
    })
    expect(screen.getByText(ARTICLES[1].title!)).toBeInTheDocument()
  })

  it('never renders a fabricated difficulty/level badge', async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES }))
    renderHome()

    await waitFor(() => {
      expect(screen.getByText(ARTICLES[0].title!)).toBeInTheDocument()
    })
    expect(screen.queryByText(/B1|B2|Estimated/i)).not.toBeInTheDocument()
  })

  it('shows an empty state with a call to action when there are no articles', async () => {
    vi.stubGlobal('fetch', mockFetchWith())
    renderHome()

    await waitFor(() => {
      expect(screen.getAllByText(/haven't added any texts yet/i).length).toBeGreaterThan(0)
    })
    expect(screen.queryByText(/B1|B2|Estimated/i)).not.toBeInTheDocument()
  })

  it("shows the Today card's reviews-done-vs-due-remaining progress", async () => {
    vi.stubGlobal('fetch', mockFetchWith({ articles: ARTICLES, dueCount: 7 }))
    renderHome()

    expect(await screen.findByText('/ 10 reviews today')).toBeInTheDocument()
  })

  it('shows a nothing-due empty state in the Today card', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchWith({
        articles: ARTICLES,
        overview: { ...OVERVIEW, reviews_today: 0, due_now: 0 },
      }),
    )
    renderHome()

    expect(
      await screen.findByText('Nothing due today — nice work staying on top of it.'),
    ).toBeInTheDocument()
  })
})
