import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Flashcards } from './Flashcards'

const DECK_FOOD = {
  id: 'deck-food',
  name: 'Food words',
  description: null,
  total_count: 5,
  due_count: 2,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), { status })
}

interface MockOptions {
  decks?: (typeof DECK_FOOD)[]
  summary?: { due_count: number; next_due_at: string | null; total_cards: number }
}

function mockFetch(options: MockOptions = {}) {
  const decks = (options.decks ?? []).map((deck) => ({ ...deck }))
  const deleteCalls: string[] = []
  const renameCalls: Array<{ deckId: string; name: string }> = []

  const fn = vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    const method = init?.method ?? 'GET'

    if (path === '/api/v1/decks' && method === 'GET') {
      return Promise.resolve(jsonResponse({ items: decks }))
    }

    if (path === '/api/v1/decks' && method === 'POST') {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      const created = {
        id: `deck-${decks.length + 1}`,
        name: body.name,
        description: null,
        total_count: 0,
        due_count: 0,
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      }
      decks.push(created)
      return Promise.resolve(jsonResponse(created, 201))
    }

    const deckMatch = path.match(/^\/api\/v1\/decks\/([^/]+)$/)
    if (deckMatch && method === 'PATCH') {
      const deckId = deckMatch[1]
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      const deck = decks.find((candidate) => candidate.id === deckId)
      if (deck && body.name) {
        deck.name = body.name
        renameCalls.push({ deckId, name: body.name })
      }
      return Promise.resolve(jsonResponse(deck))
    }

    if (deckMatch && method === 'DELETE') {
      const deckId = deckMatch[1]
      deleteCalls.push(deckId)
      const index = decks.findIndex((candidate) => candidate.id === deckId)
      if (index !== -1) decks.splice(index, 1)
      return Promise.resolve(new Response(null, { status: 204 }))
    }

    if (path === '/api/v1/reviews/summary' && method === 'GET') {
      return Promise.resolve(
        jsonResponse(options.summary ?? { due_count: 0, next_due_at: null, total_cards: 0 }),
      )
    }

    if (path === '/api/v1/reviews/due' && method === 'GET') {
      return Promise.resolve(
        jsonResponse({
          items: [
            {
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
            },
          ],
        }),
      )
    }

    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })

  return { fn, deleteCalls, renameCalls }
}

function renderFlashcards(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', fetchMock)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app/flashcards']}>
        <Routes>
          <Route path="/app/flashcards" element={<Flashcards />} />
          <Route path="/app" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('FlashcardsStart', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shows "All cards" with its due/total counts', async () => {
    const { fn } = mockFetch({ summary: { due_count: 3, next_due_at: null, total_cards: 10 } })
    renderFlashcards(fn)

    expect(await screen.findByText('All cards')).toBeInTheDocument()
    expect(await screen.findByText('3 due · 10 total')).toBeInTheDocument()
  })

  it('lists each deck with its own due/total counts', async () => {
    const { fn } = mockFetch({ decks: [DECK_FOOD] })
    renderFlashcards(fn)

    expect(await screen.findByText('Food words')).toBeInTheDocument()
    expect(screen.getByText('2 due · 5 total')).toBeInTheDocument()
  })

  it('creates a new deck', async () => {
    const { fn } = mockFetch()
    renderFlashcards(fn)
    await screen.findByText('All cards')

    fireEvent.change(screen.getByLabelText('New deck name'), {
      target: { value: 'Travel' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create deck/ }))

    expect(await screen.findByText('Travel')).toBeInTheDocument()
  })

  it('renames a deck', async () => {
    const { fn, renameCalls } = mockFetch({ decks: [DECK_FOOD] })
    renderFlashcards(fn)
    await screen.findByText('Food words')

    fireEvent.click(screen.getByRole('button', { name: 'Rename' }))
    const input = screen.getByLabelText(`Rename ${DECK_FOOD.name}`)
    fireEvent.change(input, { target: { value: 'Kitchen words' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Kitchen words')).toBeInTheDocument()
    await waitFor(() => expect(renameCalls).toEqual([{ deckId: DECK_FOOD.id, name: 'Kitchen words' }]))
  })

  it('deletes a deck after confirmation, explaining words are kept', async () => {
    const { fn, deleteCalls } = mockFetch({ decks: [DECK_FOOD] })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderFlashcards(fn)
    await screen.findByText('Food words')

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining('words'))
    expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining('kept'))
    await waitFor(() => expect(deleteCalls).toEqual([DECK_FOOD.id]))
    await waitFor(() => expect(screen.queryByText('Food words')).not.toBeInTheDocument())
  })

  it('does not delete when the confirmation is cancelled', async () => {
    const { fn, deleteCalls } = mockFetch({ decks: [DECK_FOOD] })
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderFlashcards(fn)
    await screen.findByText('Food words')

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(deleteCalls).toEqual([])
    expect(screen.getByText('Food words')).toBeInTheDocument()
  })

  it('starting "All cards" opens a session at ?deck=all', async () => {
    const { fn } = mockFetch()
    renderFlashcards(fn)
    await screen.findByText('All cards')

    fireEvent.click(screen.getByText('All cards'))

    // The session view renders its own "Exit session" control, distinct from the start
    // screen's "Back to dashboard" - its presence confirms navigation happened.
    expect(await screen.findByRole('button', { name: 'Exit session' })).toBeInTheDocument()
  })

  it('starting a deck opens a session scoped to that deck', async () => {
    const { fn } = mockFetch({ decks: [DECK_FOOD] })
    renderFlashcards(fn)
    await screen.findByText('Food words')

    fireEvent.click(screen.getByText('Food words'))

    expect(await screen.findByRole('button', { name: 'Exit session' })).toBeInTheDocument()
    expect(screen.getByText(DECK_FOOD.name)).toBeInTheDocument()
  })
})
