import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsOverview } from '../types/analytics'
import { Sidebar } from './Sidebar'

const ZERO_OVERVIEW: AnalyticsOverview = {
  words_saved: 0,
  words_mature: 0,
  words_saved_this_week: 0,
  reviews_today: 0,
  reviews_this_week: 0,
  due_now: 0,
  texts_opened_this_week: 0,
  streak: { current_days: 0, longest_days: 0, last_7_days: Array(7).fill(false) },
  recommendation: { type: 'add_text', reason: 'Add a new text', article_id: null },
}

interface MockOptions {
  dueCount?: number
  overview?: AnalyticsOverview
}

function mockFetchByUrl({ dueCount = 0, overview = ZERO_OVERVIEW }: MockOptions = {}) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()

    if (href.includes('/me')) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: 'user-1',
            username: 'alex_morgan',
            email: 'alex@example.com',
            email_verified: false,
            created_at: new Date().toISOString(),
          }),
          { status: 200 },
        ),
      )
    }

    if (href.includes('/analytics/overview')) {
      return Promise.resolve(new Response(JSON.stringify(overview), { status: 200 }))
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

function renderSidebar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Sidebar open={false} onClose={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Sidebar navigation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('marks Home as the active link on the root app route', () => {
    vi.stubGlobal('fetch', mockFetchByUrl())
    renderSidebar()

    expect(screen.getByRole('link', { name: /home/i })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /my vocabulary/i })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('moves aria-current to the clicked link', () => {
    vi.stubGlobal('fetch', mockFetchByUrl())
    renderSidebar()

    fireEvent.click(screen.getByRole('link', { name: /my vocabulary/i }))

    expect(screen.getByRole('link', { name: /my vocabulary/i })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: /home/i })).not.toHaveAttribute('aria-current')
  })

  it('shows the real signed-in user in the account card', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl())
    renderSidebar()

    expect(await screen.findByText('alex_morgan')).toBeInTheDocument()
    expect(screen.getByText('alex@example.com')).toBeInTheDocument()
  })

  it('shows the real due-card count badge next to Flashcards', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl({ dueCount: 5 }))
    renderSidebar()

    expect(await screen.findByText('5')).toBeInTheDocument()
  })

  it('hides the badge when nothing is due', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl())
    renderSidebar()

    await screen.findByText('alex_morgan')
    const flashcardsLink = screen.getByRole('link', { name: /flashcards/i })
    expect(flashcardsLink.querySelector('span.ml-auto')).not.toBeInTheDocument()
  })

  it('shows the real streak and dims the day dots with no activity', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl())
    renderSidebar()

    expect(await screen.findByText('0-day streak')).toBeInTheDocument()
    expect(screen.getByText('Review a word today to start a streak.')).toBeInTheDocument()
  })

  it('shows a positive streak and the "building a habit" copy', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchByUrl({
        overview: {
          ...ZERO_OVERVIEW,
          streak: {
            current_days: 4,
            longest_days: 9,
            last_7_days: [false, false, false, true, true, true, true],
          },
        },
      }),
    )
    renderSidebar()

    expect(await screen.findByText('4-day streak')).toBeInTheDocument()
    expect(screen.getByText("You're building a habit!")).toBeInTheDocument()
  })
})
