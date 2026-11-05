import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { VocabularyItem } from '../../types/vocabulary'
import { Vocabulary } from './Vocabulary'

const ITEM_NOUN: VocabularyItem = {
  id: 'item-herausforderung',
  lemma: 'Herausforderung',
  display_form: 'Herausforderung',
  meaning: 'challenge',
  translation: 'challenge',
  part_of_speech: 'NOUN',
  grammar_metadata: { gender: 'Fem', plural: 'Herausforderungen' },
  notes: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const ITEM_PHRASE: VocabularyItem = {
  id: 'item-gewoehnen',
  lemma: 'sich gewöhnen an',
  display_form: 'gewöhnen an',
  meaning: 'to get used to',
  translation: null,
  part_of_speech: 'PHRASE',
  grammar_metadata: {},
  notes: null,
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
}

const ALL_ITEMS = [ITEM_PHRASE, ITEM_NOUN]

function jsonResponse(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), { status })
}

interface MockOptions {
  items?: VocabularyItem[]
}

function mockFetch(options: MockOptions = {}) {
  // Mutable copy: PATCH/DELETE below must be reflected in later GETs (e.g. after the
  // component invalidates and refetches), or an edit would look reverted in the UI.
  const items = (options.items ?? ALL_ITEMS).map((item) => ({ ...item }))

  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    const method = init?.method ?? 'GET'

    if (path === '/api/v1/vocabulary' && method === 'GET') {
      const search = url.searchParams.get('search')?.toLowerCase() ?? ''
      const pos = url.searchParams.get('pos') ?? ''
      const filtered = items.filter(
        (item) =>
          (!search ||
            item.display_form.toLowerCase().includes(search) ||
            item.lemma.toLowerCase().includes(search)) &&
          (!pos || item.part_of_speech === pos),
      )
      return Promise.resolve(
        jsonResponse({ items: filtered, total: filtered.length, page: 1, page_size: 20 }),
      )
    }

    const detailMatch = path.match(/^\/api\/v1\/vocabulary\/(.+)$/)
    if (detailMatch && method === 'GET') {
      const item = items.find((candidate) => candidate.id === detailMatch[1])
      if (!item) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      return Promise.resolve(
        jsonResponse({
          ...item,
          occurrences: [
            {
              id: 'occ-1',
              article_id: 'article-1',
              start_offset: 10,
              end_offset: 10 + item.display_form.length,
              context_sentence: `Das war eine große ${item.display_form}.`,
              created_at: item.created_at,
            },
          ],
        }),
      )
    }

    if (detailMatch && method === 'PATCH') {
      const item = items.find((candidate) => candidate.id === detailMatch[1])
      if (!item) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      Object.assign(item, body)
      return Promise.resolve(jsonResponse(item))
    }

    if (detailMatch && method === 'DELETE') {
      const index = items.findIndex((candidate) => candidate.id === detailMatch[1])
      if (index !== -1) items.splice(index, 1)
      return Promise.resolve(jsonResponse(null, 204))
    }

    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })
}

function renderVocabulary(initialEntry = '/app/vocabulary') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/app/vocabulary" element={<Vocabulary />} />
          <Route path="/app/reader/new" element={<div>Add text</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Vocabulary page', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('lists saved words and expressions with their meaning', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary()

    expect(await screen.findByText('Herausforderung')).toBeInTheDocument()
    expect(screen.getByText('gewöhnen an')).toBeInTheDocument()
    expect(screen.getByText('challenge')).toBeInTheDocument()
    expect(screen.getByText('to get used to')).toBeInTheDocument()
  })

  it('shows an empty state with a call to action when nothing is saved yet', async () => {
    vi.stubGlobal('fetch', mockFetch({ items: [] }))
    renderVocabulary()

    expect(
      await screen.findByText(/haven't saved any words yet/),
    ).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Add a text/ }).length).toBeGreaterThan(0)
  })

  it('filters the list as the user types a search query', async () => {
    const fetchMock = mockFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.change(screen.getByLabelText('Search your vocabulary'), {
      target: { value: 'Heraus' },
    })

    await waitFor(
      () => {
        const sawSearch = fetchMock.mock.calls.some((call) =>
          String(call[0]).includes('search=Heraus'),
        )
        expect(sawSearch).toBe(true)
      },
      { timeout: 1000 },
    )
    expect(await screen.findByText('Herausforderung')).toBeInTheDocument()
    expect(screen.queryByText('gewöhnen an')).not.toBeInTheDocument()
  })

  it('filters the list by word type', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.change(screen.getByLabelText('Filter by word type'), {
      target: { value: 'PHRASE' },
    })

    await waitFor(() => {
      expect(screen.getByText('gewöhnen an')).toBeInTheDocument()
    })
    expect(screen.queryByText('Herausforderung')).not.toBeInTheDocument()
  })

  it('opens the detail drawer with occurrences and a link back to the article', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.click(screen.getByText('Herausforderung'))

    expect(await screen.findByText('Plural: Herausforderungen')).toBeInTheDocument()
    expect(screen.getByText(/Das war eine große/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Open in article/ })).toBeInTheDocument()
  })

  it('edits a saved item and persists the change', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary()
    await screen.findByText('Herausforderung')
    fireEvent.click(screen.getByText('Herausforderung'))
    await screen.findByText('Plural: Herausforderungen')

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    const meaningInput = screen.getByLabelText('Meaning')
    fireEvent.change(meaningInput, { target: { value: 'big challenge' } })
    fireEvent.click(screen.getByRole('button', { name: /Save changes/ }))

    expect(await screen.findByText('big challenge')).toBeInTheDocument()
  })

  it('deletes a saved item after confirmation', async () => {
    vi.stubGlobal('fetch', mockFetch())
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderVocabulary()
    await screen.findByText('Herausforderung')
    fireEvent.click(screen.getByText('Herausforderung'))
    await screen.findByText('Plural: Herausforderungen')

    fireEvent.click(screen.getByRole('button', { name: /Delete from vocabulary/ }))

    await waitFor(() => {
      expect(screen.queryByText('Plural: Herausforderungen')).not.toBeInTheDocument()
    })
  })

  it('opens the drawer directly from an ?item= query parameter', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary('/app/vocabulary?item=item-herausforderung')

    expect(await screen.findByText('Plural: Herausforderungen')).toBeInTheDocument()
  })
})
