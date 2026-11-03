import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Signup } from './Signup'

function renderSignup() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/signup']}>
        <Routes>
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-email" element={<div>Verify Email Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function fillForm({
  username = 'alex_morgan',
  email = 'alex@example.com',
  password = 'correcthorsebatterystaple',
  confirmPassword = password,
}: {
  username?: string
  email?: string
  password?: string
  confirmPassword?: string
} = {}) {
  fireEvent.change(screen.getByLabelText(/username/i), { target: { value: username } })
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: email } })
  fireEvent.change(screen.getByLabelText(/^password/i), { target: { value: password } })
  fireEvent.change(screen.getByLabelText(/confirm password/i), {
    target: { value: confirmPassword },
  })
}

describe('Signup', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a field error and does not submit when passwords do not match', () => {
    vi.stubGlobal('fetch', vi.fn())
    renderSignup()

    fillForm({ password: 'correcthorsebatterystaple', confirmPassword: 'somethingelse' })
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByText('Passwords must match.')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('shows a field error for an invalid username without calling the API', () => {
    vi.stubGlobal('fetch', vi.fn())
    renderSignup()

    fillForm({ username: 'ab' })
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByText(/username must be 3-30 characters/i)).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('redirects to /verify-email after a successful signup', async () => {
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
          { status: 201 },
        ),
      ),
    )
    renderSignup()

    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('Verify Email Page')).toBeInTheDocument()
  })

  it('shows the server field error when the username is already taken', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: [
              { loc: ['body', 'username'], msg: 'This username is already taken.', type: 'value_error.conflict' },
            ],
          }),
          { status: 409 },
        ),
      ),
    )
    renderSignup()

    fillForm()
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('This username is already taken.')).toBeInTheDocument()
  })
})
