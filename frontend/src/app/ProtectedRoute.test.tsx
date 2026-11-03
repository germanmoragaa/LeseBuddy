import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProtectedRoute } from './ProtectedRoute'

function renderProtected(initialEntry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<div>App Home</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/verify-email" element={<div>Verify Email Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ProtectedRoute', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects to /login when not authenticated', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))

    renderProtected('/app')

    expect(await screen.findByText('Login Page')).toBeInTheDocument()
  })

  it('renders the protected content when authenticated and verified', async () => {
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

    renderProtected('/app')

    expect(await screen.findByText('App Home')).toBeInTheDocument()
  })

  it('redirects to /verify-email when authenticated but unverified', async () => {
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

    renderProtected('/app')

    expect(await screen.findByText('Verify Email Page')).toBeInTheDocument()
  })
})
