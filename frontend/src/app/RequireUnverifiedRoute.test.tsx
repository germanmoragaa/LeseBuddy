import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RequireUnverifiedRoute } from './RequireUnverifiedRoute'

function renderRequireUnverified(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<RequireUnverifiedRoute />}>
            <Route path="/verify-email" element={<div>Verify Email Page</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/app" element={<div>App Home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RequireUnverifiedRoute', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects logged-out visitors to /login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))

    renderRequireUnverified('/verify-email')

    expect(await screen.findByText('Login Page')).toBeInTheDocument()
  })

  it('redirects already-verified users to /app', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: 'user-1',
            username: 'alex_morgan',
            email: 'alex@example.com',
            email_verified: true,
            created_at: new Date().toISOString(),
          }),
          { status: 200 },
        ),
      ),
    )

    renderRequireUnverified('/verify-email')

    expect(await screen.findByText('App Home')).toBeInTheDocument()
  })

  it('renders the verification page for unverified users', async () => {
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

    renderRequireUnverified('/verify-email')

    expect(await screen.findByText('Verify Email Page')).toBeInTheDocument()
  })
})
