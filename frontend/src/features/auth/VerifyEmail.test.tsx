import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { VerifyEmail } from './VerifyEmail'

const baseUser = {
  id: 'user-1',
  username: 'alex_morgan',
  email: 'alex@example.com',
  email_verified: false,
  created_at: new Date().toISOString(),
}

function jsonResponse(body: unknown, status: number) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status })
}

function mockFetch({
  verifyEmail,
  resend,
  logout,
}: {
  verifyEmail?: { status: number; body?: unknown }
  resend?: { status: number; body?: unknown }
  logout?: { status: number }
}) {
  return vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    if (url.endsWith('/me') && method === 'GET') {
      return Promise.resolve(jsonResponse(baseUser, 200))
    }
    if (url.endsWith('/auth/verify-email') && method === 'POST' && verifyEmail) {
      return Promise.resolve(jsonResponse(verifyEmail.body, verifyEmail.status))
    }
    if (url.endsWith('/auth/resend-verification') && method === 'POST' && resend) {
      return Promise.resolve(jsonResponse(resend.body, resend.status))
    }
    if (url.endsWith('/auth/logout') && method === 'POST') {
      return Promise.resolve(jsonResponse(undefined, logout?.status ?? 204))
    }
    return Promise.reject(new Error(`Unexpected fetch: ${method} ${url}`))
  })
}

function renderVerifyEmail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/verify-email']}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/app" element={<div>App Home</div>} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function fillCode(code: string) {
  fireEvent.change(screen.getByLabelText(/verification code/i), { target: { value: code } })
}

describe('VerifyEmail', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it("shows the user's email and the resend cooldown on load", async () => {
    vi.stubGlobal('fetch', mockFetch({}))

    renderVerifyEmail()

    expect(await screen.findByText(/alex@example.com/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /resend code \(60s\)/i })).toBeDisabled()
  })

  it('verifies with the correct code and navigates to /app', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({ verifyEmail: { status: 200, body: { ...baseUser, email_verified: true } } }),
    )
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    fillCode('123456')
    fireEvent.click(screen.getByRole('button', { name: /verify email/i }))

    expect(await screen.findByText('App Home')).toBeInTheDocument()
  })

  it('shows an error message for an incorrect code', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        verifyEmail: {
          status: 400,
          body: { detail: { code: 'invalid_code', message: 'Incorrect code. Please try again.' } },
        },
      }),
    )
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    fillCode('000000')
    fireEvent.click(screen.getByRole('button', { name: /verify email/i }))

    expect(await screen.findByText('Incorrect code. Please try again.')).toBeInTheDocument()
  })

  it('shows an error message for an expired code', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        verifyEmail: {
          status: 400,
          body: {
            detail: {
              code: 'code_expired',
              message: 'This code has expired. Please request a new code.',
            },
          },
        },
      }),
    )
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    fillCode('123456')
    fireEvent.click(screen.getByRole('button', { name: /verify email/i }))

    expect(
      await screen.findByText('This code has expired. Please request a new code.'),
    ).toBeInTheDocument()
  })

  it('shows an error message after too many incorrect attempts', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        verifyEmail: {
          status: 400,
          body: {
            detail: {
              code: 'too_many_attempts',
              message: 'Too many incorrect attempts. Please request a new code.',
            },
          },
        },
      }),
    )
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    fillCode('123456')
    fireEvent.click(screen.getByRole('button', { name: /verify email/i }))

    expect(
      await screen.findByText('Too many incorrect attempts. Please request a new code.'),
    ).toBeInTheDocument()
  })

  it('enables resend once the cooldown reaches zero, then counts down again after a successful resend', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    vi.stubGlobal('fetch', mockFetch({ resend: { status: 204 } }))
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    const resendButton = screen.getByRole('button', { name: /^resend code$/i })
    expect(resendButton).toBeEnabled()

    fireEvent.click(resendButton)

    expect(
      await screen.findByRole('button', { name: /resend code \(60s\)/i }),
    ).toBeDisabled()
  })

  it('shows a rate-limit message and the server-provided countdown on 429', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    vi.stubGlobal(
      'fetch',
      mockFetch({
        resend: {
          status: 429,
          body: { detail: { code: 'resend_cooldown', message: 'Too soon.', retry_after: 45 } },
        },
      }),
    )
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    act(() => {
      vi.advanceTimersByTime(60_000)
    })
    fireEvent.click(screen.getByRole('button', { name: /^resend code$/i }))

    expect(
      await screen.findByText('Please wait before requesting another code.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /resend code \(45s\)/i })).toBeDisabled()
  })

  it('logs out and navigates to /login', async () => {
    vi.stubGlobal('fetch', mockFetch({}))
    renderVerifyEmail()
    await screen.findByText(/alex@example.com/)

    fireEvent.click(screen.getByRole('button', { name: /log out/i }))

    expect(await screen.findByText('Login Page')).toBeInTheDocument()
  })
})
