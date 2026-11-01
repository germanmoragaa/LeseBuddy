import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Sidebar } from './Sidebar'

function renderSidebar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <Sidebar open={false} onClose={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Sidebar navigation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('marks Home as the active link on the root route', () => {
    renderSidebar()

    expect(screen.getByRole('link', { name: /home/i })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /my vocabulary/i })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('moves aria-current to the clicked link', () => {
    renderSidebar()

    fireEvent.click(screen.getByRole('link', { name: /my vocabulary/i }))

    expect(screen.getByRole('link', { name: /my vocabulary/i })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: /home/i })).not.toHaveAttribute('aria-current')
  })
})
