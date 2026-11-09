import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DueFlashcard } from '../../types/flashcards'
import { Flashcards } from './Flashcards'

const CARD_HUND: DueFlashcard = {
  id: 'card-hund',
  vocabulary_item_id: 'item-hund',
  due_at: '2026-01-01T00:00:00Z',
  front: { display_form: 'Hund', part_of_speech: 'NOUN', gender: 'Masc' },
  back: {
    translation: 'dog',
    glosses: ['a domesticated canine'],
    part_of_speech: 'NOUN',
    context_sentence: 'Der Hund schläft.',
  },
  preview: { again: 0, hard: 1, good: 1, easy: 4 },
}

const CARD_BUCH: DueFlashcard = {
  id: 'card-buch',
  vocabulary_item_id: 'item-buch',
  due_at: '2026-01-01T00:00:00Z',
  front: { display_form: 'Buch', part_of_speech: 'NOUN', gender: 'Neut' },
  back: {
    translation: 'book',
    glosses: ['a bound collection of pages'],
    part_of_speech: 'NOUN',
    context_sentence: 'Das Buch liegt da.',
  },
  preview: { again: 0, hard: 1, good: 1, easy: 4 },
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), { status })
}

interface MockOptions {
  dueItems?: DueFlashcard[]
  nextDueItems?: DueFlashcard[]
  summary?: { due_count: number; next_due_at: string | null; total_cards: number }
  failFirstReview?: boolean
}

function mockFetch(options: MockOptions = {}) {
  let dueCallCount = 0
  let failFirstReview = options.failFirstReview ?? false
  const reviewCalls: Array<{ flashcard_id: string; rating: string; client_review_id?: string }> =
    []

  const fn = vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    const method = init?.method ?? 'GET'

    if (path === '/api/v1/reviews/due' && method === 'GET') {
      dueCallCount += 1
      const items = dueCallCount === 1 ? (options.dueItems ?? []) : (options.nextDueItems ?? [])
      return Promise.resolve(jsonResponse({ items }))
    }

    if (path === '/api/v1/reviews/summary' && method === 'GET') {
      return Promise.resolve(
        jsonResponse(options.summary ?? { due_count: 0, next_due_at: null, total_cards: 0 }),
      )
    }

    if (path === '/api/v1/reviews' && method === 'POST') {
      const body = JSON.parse(String(init?.body))
      reviewCalls.push(body)
      if (failFirstReview) {
        failFirstReview = false
        return Promise.resolve(jsonResponse({ detail: 'error' }, 500))
      }
      return Promise.resolve(
        jsonResponse({
          flashcard_id: body.flashcard_id,
          rating: body.rating,
          ease_factor: 2.5,
          interval_days: 1,
          due_at: '2026-01-02T00:00:00Z',
          reviewed_at: '2026-01-01T12:00:00Z',
        }),
      )
    }

    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })

  return { fn, reviewCalls }
}

function renderFlashcards(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app/flashcards']}>
        <Routes>
          <Route path="/app/flashcards" element={<Flashcards />} />
          <Route path="/app" element={<div>Dashboard</div>} />
          <Route path="/app/reader" element={<div>Reading library</div>} />
          <Route path="/app/vocabulary" element={<div>Vocabulary</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...result, queryClient }
}

describe('Flashcards', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shows an empty state with CTAs when nothing is due', async () => {
    const { fn } = mockFetch({
      dueItems: [],
      summary: { due_count: 0, next_due_at: '2026-01-02T09:00:00Z', total_cards: 5 },
    })
    renderFlashcards(fn)

    expect(await screen.findByText("You're all caught up!")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Read something new' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Browse your vocabulary' })).toBeInTheDocument()
  })

  it('reveals the answer via the button', async () => {
    const { fn } = mockFetch({ dueItems: [CARD_HUND], nextDueItems: [] })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    expect(screen.queryByText('dog')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))

    expect(await screen.findByText('dog')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2 }).textContent).toContain('der Hund')
  })

  it('reveals the answer via Space', async () => {
    const { fn } = mockFetch({ dueItems: [CARD_HUND], nextDueItems: [] })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    fireEvent.keyDown(window, { code: 'Space', key: ' ' })

    expect(await screen.findByText('dog')).toBeInTheDocument()
  })

  it('rating via button sends the payload with a client_review_id', async () => {
    const { fn, reviewCalls } = mockFetch({ dueItems: [CARD_HUND], nextDueItems: [] })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))
    await screen.findByText('dog')

    fireEvent.click(screen.getByRole('button', { name: /Good/ }))

    await waitFor(() => expect(reviewCalls).toHaveLength(1))
    expect(reviewCalls[0].flashcard_id).toBe('card-hund')
    expect(reviewCalls[0].rating).toBe('good')
    expect(reviewCalls[0].client_review_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    )
  })

  it('invalidates the reviews cache after a successful rating', async () => {
    const { fn } = mockFetch({ dueItems: [CARD_HUND], nextDueItems: [] })
    const { queryClient } = renderFlashcards(fn)
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    await screen.findByText('Hund')
    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))
    await screen.findByText('dog')
    fireEvent.click(screen.getByRole('button', { name: /Good/ }))

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['reviews'] })
    })
  })

  it('rating via keys 1-4 sends the right rating', async () => {
    const { fn, reviewCalls } = mockFetch({ dueItems: [CARD_HUND], nextDueItems: [] })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    fireEvent.keyDown(window, { code: 'Space', key: ' ' })
    await screen.findByText('dog')

    fireEvent.keyDown(window, { key: '3' }) // good

    await waitFor(() => expect(reviewCalls).toHaveLength(1))
    expect(reviewCalls[0].rating).toBe('good')
  })

  it('retry after an error reuses the same client_review_id', async () => {
    const { fn, reviewCalls } = mockFetch({
      dueItems: [CARD_HUND],
      nextDueItems: [],
      failFirstReview: true,
    })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))
    await screen.findByText('dog')
    fireEvent.click(screen.getByRole('button', { name: /Good/ }))

    expect(await screen.findByText("Couldn't save that review.")).toBeInTheDocument()
    await waitFor(() => expect(reviewCalls).toHaveLength(1))

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(reviewCalls).toHaveLength(2))
    expect(reviewCalls[1].client_review_id).toBe(reviewCalls[0].client_review_id)
    expect(reviewCalls[1].rating).toBe('good')
  })

  it('shows session complete with correct counts once the batch is exhausted', async () => {
    const { fn } = mockFetch({
      dueItems: [CARD_HUND, CARD_BUCH],
      nextDueItems: [],
      summary: { due_count: 0, next_due_at: '2026-01-03T08:00:00Z', total_cards: 2 },
    })
    renderFlashcards(fn)

    await screen.findByText('Hund')
    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))
    await screen.findByText('dog')
    fireEvent.click(screen.getByRole('button', { name: /Good/ }))

    await screen.findByText('Buch')
    fireEvent.click(screen.getByRole('button', { name: 'Reveal answer' }))
    await screen.findByText('book')
    fireEvent.click(screen.getByRole('button', { name: /Easy/ }))

    expect(await screen.findByText('Session complete!')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument() // cards reviewed
    const goodCount = screen.getByText('Good').parentElement
    expect(goodCount?.textContent).toContain('1')
    const easyCount = screen.getByText('Easy').parentElement
    expect(easyCount?.textContent).toContain('1')
  })
})
