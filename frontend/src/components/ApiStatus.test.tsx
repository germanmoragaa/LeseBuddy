import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiStatus } from './ApiStatus'

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>,
  )
}

describe('ApiStatus', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the API status on success', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    )

    renderWithQueryClient(<ApiStatus />)

    await waitFor(() => {
      expect(screen.getByText('API status: ok')).toBeInTheDocument()
    })
  })

  it('shows an error state when the request fails', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 500 }))

    renderWithQueryClient(<ApiStatus />)

    await waitFor(() => {
      expect(screen.getByText('API status: error')).toBeInTheDocument()
    })
  })
})
