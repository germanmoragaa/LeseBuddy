import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DueFlashcard } from '../../types/flashcards'
import { PracticeCard } from './PracticeCard'

const CARD: DueFlashcard = {
  id: 'card-1',
  vocabulary_item_id: 'item-1',
  due_at: '2026-01-01T00:00:00Z',
  front: { display_form: 'die Herausforderung', part_of_speech: 'NOUN', gender: 'Fem' },
  back: {
    translation: 'challenge',
    glosses: ['challenge'],
    part_of_speech: 'NOUN',
    context_sentence: 'Das ist eine große Herausforderung.',
  },
  preview: { again: 0, hard: 1, good: 1, easy: 4 },
}

function mockFetch(dueItems: DueFlashcard[], dueCount: number) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/reviews/due')) {
      return Promise.resolve(new Response(JSON.stringify({ items: dueItems }), { status: 200 }))
    }
    if (href.includes('/reviews/summary')) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ due_count: dueCount, next_due_at: null, total_cards: dueCount }),
          { status: 200 },
        ),
      )
    }
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderPracticeCard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={<PracticeCard />} />
          <Route path="/app/flashcards" element={<div>Flashcards screen</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PracticeCard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows due cards with a real due count', async () => {
    vi.stubGlobal('fetch', mockFetch([CARD], 4))
    renderPracticeCard()

    expect(await screen.findByText('die Herausforderung')).toBeInTheDocument()
    expect(screen.getByText('challenge')).toBeInTheDocument()
    expect(screen.getByText('4 due')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review 4 cards' })).toBeInTheDocument()
  })

  it('shows an empty state and disables the button when nothing is due', async () => {
    vi.stubGlobal('fetch', mockFetch([], 0))
    renderPracticeCard()

    expect(
      await screen.findByText(/Nothing due right now/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/due$/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nothing to review' })).toBeDisabled()
  })

  it('navigates to the flashcards screen when a card is clicked', async () => {
    vi.stubGlobal('fetch', mockFetch([CARD], 1))
    renderPracticeCard()

    fireEvent.click(await screen.findByText('die Herausforderung'))

    expect(await screen.findByText('Flashcards screen')).toBeInTheDocument()
  })
})
