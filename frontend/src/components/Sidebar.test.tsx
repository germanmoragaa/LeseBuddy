import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Sidebar } from './Sidebar'

function mockFetchByUrl(dueCount: number) {
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
    vi.stubGlobal('fetch', mockFetchByUrl(0))
    renderSidebar()

    expect(screen.getByRole('link', { name: /home/i })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /my vocabulary/i })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('moves aria-current to the clicked link', () => {
    vi.stubGlobal('fetch', mockFetchByUrl(0))
    renderSidebar()

    fireEvent.click(screen.getByRole('link', { name: /my vocabulary/i }))

    expect(screen.getByRole('link', { name: /my vocabulary/i })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: /home/i })).not.toHaveAttribute('aria-current')
  })

  it('shows the real signed-in user in the account card', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl(0))
    renderSidebar()

    expect(await screen.findByText('alex_morgan')).toBeInTheDocument()
    expect(screen.getByText('alex@example.com')).toBeInTheDocument()
  })

  it('shows the real due-card count badge next to Flashcards', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl(5))
    renderSidebar()

    expect(await screen.findByText('5')).toBeInTheDocument()
  })

  it('hides the badge when nothing is due', async () => {
    vi.stubGlobal('fetch', mockFetchByUrl(0))
    renderSidebar()

    await screen.findByText('alex_morgan')
    const flashcardsLink = screen.getByRole('link', { name: /flashcards/i })
    expect(flashcardsLink.querySelector('span.ml-auto')).not.toBeInTheDocument()
  })
})
