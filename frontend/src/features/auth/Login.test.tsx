import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Login } from './Login'

function renderLogin() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/app" element={<div>App Home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function submitLogin(identifier: string, password: string) {
  fireEvent.change(screen.getByLabelText(/email or username/i), {
    target: { value: identifier },
  })
  fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: /log in/i }))
}

describe('Login', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects to /app on success', async () => {
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
    renderLogin()

    submitLogin('alex_morgan', 'correcthorsebatterystaple')

    expect(await screen.findByText('App Home')).toBeInTheDocument()
  })

  it('shows a generic error on invalid credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: 'Incorrect email/username or password.' }),
          { status: 401 },
        ),
      ),
    )
    renderLogin()

    submitLogin('alex_morgan', 'wrong-password')

    expect(await screen.findByText('Incorrect email/username or password.')).toBeInTheDocument()
  })

  it('shows the rate-limit message on 429', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: 'Too many failed login attempts. Please try again in 15 minutes.' }),
          { status: 429 },
        ),
      ),
    )
    renderLogin()

    submitLogin('alex_morgan', 'wrong-password')

    expect(
      await screen.findByText('Too many failed login attempts. Please try again in 15 minutes.'),
    ).toBeInTheDocument()
  })
})
