import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AppRouter } from './router'

const TEST_USERNAME = 'alex_morgan'

function meResponse() {
  return new Response(
    JSON.stringify({
      id: 'user-1',
      username: TEST_USERNAME,
      email: 'alex@example.com',
      email_verified: true,
      created_at: new Date().toISOString(),
    }),
    { status: 200 },
  )
}

// Simulates a backend that hasn't picked up the paginated { items, total, page, page_size }
// response shape yet (e.g. a dev server running stale code) — the frontend must degrade
// gracefully instead of crashing the whole app to a blank page.
function staleShapeArticlesResponse() {
  return new Response(JSON.stringify([]), { status: 200 })
}

function mockFetchWithStaleArticlesShape() {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/me')) return Promise.resolve(meResponse())
    if (href.includes('/articles')) return Promise.resolve(staleShapeArticlesResponse())
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderAppAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AppRouter />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AppRouter', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the dashboard at /app without crashing when the articles API returns an unexpected (non-paginated) shape', async () => {
    vi.stubGlobal('fetch', mockFetchWithStaleArticlesShape())
    const { container } = renderAppAt('/app')

    // "Pick up where you left off" renders unconditionally on mount (before the articles
    // query resolves), so it alone wouldn't catch a crash that only happens once the query
    // settles. Wait for the error copy that only renders *after* the query settles — a bare
    // array (the stale, pre-pagination shape) must surface as an error, not as "no articles",
    // since silently treating it as empty would hide real, persisted articles from the user.
    await waitFor(() => {
      expect(screen.getByText(/couldn't load your reading library/i)).toBeInTheDocument()
    })

    expect(container.textContent?.trim().length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.queryByText(/haven't added any texts yet/i)).not.toBeInTheDocument()
  })
})
