import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { PublicOnlyRoute } from './PublicOnlyRoute'

function renderPublicOnly(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/" element={<div>Welcome Page</div>} />
          </Route>
          <Route path="/app" element={<div>App Home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PublicOnlyRoute', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the public page for logged-out visitors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))

    renderPublicOnly('/')

    expect(await screen.findByText('Welcome Page')).toBeInTheDocument()
  })

  it('redirects already-authenticated users to /app', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
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
      ),
    )

    renderPublicOnly('/')

    expect(await screen.findByText('App Home')).toBeInTheDocument()
  })
})
