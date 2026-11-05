import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddText } from './AddText'

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

interface MockOptions {
  fail?: boolean
  failStatus?: number
  delayMs?: number
}

function mockFetch(options: MockOptions = {}) {
  let callCount = 0
  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const method = init?.method ?? 'GET'

    if (url.pathname === '/api/v1/articles' && method === 'POST') {
      callCount += 1
      const respond = () => {
        if (options.fail) {
          return jsonResponse({ detail: 'error' }, options.failStatus ?? 500)
        }
        const body = JSON.parse(String(init?.body))
        return jsonResponse({
          id: `article-${callCount}`,
          title: body.title ?? null,
          source_url: null,
          language: 'de',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          word_count: body.original_text.split(/\s+/).filter(Boolean).length,
          excerpt: body.original_text.slice(0, 160),
          original_text: body.original_text,
        })
      }
      if (options.delayMs) {
        return new Promise((resolve) => setTimeout(() => resolve(respond()), options.delayMs))
      }
      return Promise.resolve(respond())
    }

    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })
}

function renderAddText() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app/reader/new']}>
        <Routes>
          <Route path="/app/reader/new" element={<AddText />} />
          <Route path="/app/reader/:articleId" element={<div>Article view</div>} />
          <Route path="/app" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return queryClient
}

describe('AddText', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('disables submit until text is entered', () => {
    vi.stubGlobal('fetch', mockFetch())
    renderAddText()

    expect(screen.getByRole('button', { name: /Create reading space/ })).toBeDisabled()

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'Ein Text.' },
    })

    expect(screen.getByRole('button', { name: /Create reading space/ })).toBeEnabled()
  })

  it('submits successfully and navigates to the new article', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderAddText()

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'Ein deutscher Text.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create reading space/ }))

    expect(await screen.findByText('Article view')).toBeInTheDocument()
  })

  it('invalidates the articles cache on successful creation', async () => {
    vi.stubGlobal('fetch', mockFetch())
    const queryClient = renderAddText()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'Ein deutscher Text.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create reading space/ }))

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['articles'] })
    })
  })

  it('prevents double submission while the request is pending', async () => {
    const fetchMock = mockFetch({ delayMs: 50 })
    vi.stubGlobal('fetch', fetchMock)
    renderAddText()

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'Ein deutscher Text.' },
    })
    const submitButton = screen.getByRole('button', { name: /Create reading space/ })
    fireEvent.click(submitButton)
    const pendingButton = await screen.findByRole('button', { name: /Creating…/ })
    expect(pendingButton).toBeDisabled()
    fireEvent.click(pendingButton)
    fireEvent.click(pendingButton)

    await screen.findByText('Article view')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shows a clear error message when the server request fails', async () => {
    vi.stubGlobal('fetch', mockFetch({ fail: true }))
    renderAddText()

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'Ein deutscher Text.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create reading space/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/Something went wrong/)
  })

  it('blocks submission and shows a message when the text is too long', () => {
    vi.stubGlobal('fetch', mockFetch())
    renderAddText()

    fireEvent.change(screen.getByPlaceholderText(/Paste a German article/), {
      target: { value: 'a'.repeat(50_001) },
    })

    expect(screen.getByRole('button', { name: /Create reading space/ })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent(/too long/)
  })

  it('shows the URL tab as disabled with a "coming soon" hint instead of a working import', () => {
    vi.stubGlobal('fetch', mockFetch())
    renderAddText()

    const urlTab = screen.getByRole('button', { name: /Enter a URL/ })
    expect(urlTab).toBeDisabled()
  })

  it('keeps "Back to dashboard" working', () => {
    vi.stubGlobal('fetch', mockFetch())
    renderAddText()

    fireEvent.click(screen.getByRole('button', { name: /Back to dashboard/ }))

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})
