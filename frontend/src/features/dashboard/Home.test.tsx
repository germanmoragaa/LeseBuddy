import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  mockContinueReading,
  mockDashboardStats,
  mockRecentArticles,
} from '../../mocks/dashboard'
import { Home } from './Home'

const TEST_USERNAME = 'alex_morgan'

function mockFetchByUrl(url: string | URL | Request) {
  const href = url.toString()

  if (href.includes('/me')) {
    return Promise.resolve(
      new Response(
        JSON.stringify({
          id: 'user-1',
          username: TEST_USERNAME,
          email: 'alex@example.com',
          email_verified: false,
          created_at: new Date().toISOString(),
        }),
        { status: 200 },
      ),
    )
  }

  return Promise.resolve(new Response(null, { status: 500 }))
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
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(mockFetchByUrl))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('greets the signed-in user by username', async () => {
    renderHome()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(TEST_USERNAME)
    })
  })

  it('renders the dashboard stats from mock data', () => {
    renderHome()

    expect(screen.getByText(String(mockDashboardStats.wordsLearned))).toBeInTheDocument()
    expect(screen.getByText(String(mockDashboardStats.reviewsCompletedThisWeek))).toBeInTheDocument()
    expect(screen.getByText(`${mockDashboardStats.readingHoursThisWeek}h`)).toBeInTheDocument()
  })

  it('renders the continue-reading article and recent reading list', () => {
    renderHome()

    // The "continue reading" article is also the most recent one in the library list,
    // so its title legitimately appears twice on the page.
    expect(screen.getAllByText(mockContinueReading.title).length).toBeGreaterThanOrEqual(2)
    for (const article of mockRecentArticles.slice(1)) {
      expect(screen.getByText(article.title)).toBeInTheDocument()
    }
  })
})
