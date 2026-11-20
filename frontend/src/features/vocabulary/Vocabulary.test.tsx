import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { VocabularyItem, VocabularyOccurrence } from '../../types/vocabulary'
import { Vocabulary } from './Vocabulary'

const ITEM_NOUN: VocabularyItem = {
  id: 'item-herausforderung',
  lemma: 'Herausforderung',
  display_form: 'Herausforderung',
  meaning: 'challenge',
  translation: 'challenge',
  // Saved before `meanings` existed: the drawer falls back to the deprecated fields.
  meanings: [],
  example_occurrence_id: null,
  part_of_speech: 'NOUN',
  grammar_metadata: { gender: 'Fem', plural: 'Herausforderungen' },
  notes: null,
  deck_ids: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const ITEM_PHRASE: VocabularyItem = {
  id: 'item-gewoehnen',
  lemma: 'sich gewöhnen an',
  display_form: 'gewöhnen an',
  meaning: 'to get used to',
  translation: null,
  meanings: [{ text: 'to get used to', source: 'dictionary' }],
  example_occurrence_id: null,
  part_of_speech: 'PHRASE',
  grammar_metadata: {},
  notes: null,
  deck_ids: [],
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
}

const ALL_ITEMS = [ITEM_PHRASE, ITEM_NOUN]

const DECK_FOOD = {
  id: 'deck-food',
  name: 'Food words',
  description: null,
  total_count: 0,
  due_count: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), { status })
}

interface MockOptions {
  items?: VocabularyItem[]
  decks?: (typeof DECK_FOOD)[]
  occurrences?: VocabularyOccurrence[]
}

function defaultOccurrences(item: VocabularyItem): VocabularyOccurrence[] {
  const line = `Das war eine große ${item.display_form}.`
  return [
    {
      id: 'occ-1',
      article_id: 'article-1',
      start_offset: 10,
      end_offset: 10 + item.display_form.length,
      context_sentence: line,
      context_line: line,
      context_translation: null,
      needs_translation: true,
      created_at: item.created_at,
    },
  ]
}

function mockFetch(options: MockOptions = {}) {
  // Mutable copy: PATCH/DELETE below must be reflected in later GETs (e.g. after the
  // component invalidates and refetches), or an edit would look reverted in the UI.
  const items = (options.items ?? ALL_ITEMS).map((item) => ({ ...item }))
  const decks = (options.decks ?? []).map((deck) => ({ ...deck }))
  const occurrencesByItem = new Map<string, VocabularyOccurrence[]>()
  function occurrencesOf(item: VocabularyItem) {
    if (!occurrencesByItem.has(item.id)) {
      occurrencesByItem.set(
        item.id,
        (options.occurrences ?? defaultOccurrences(item)).map((occ) => ({ ...occ })),
      )
    }
    return occurrencesByItem.get(item.id)!
  }
  function findOccurrence(occurrenceId: string) {
    for (const item of items) {
      const match = occurrencesOf(item).find((occ) => occ.id === occurrenceId)
      if (match) return match
    }
    return undefined
  }

  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname
    const method = init?.method ?? 'GET'

    if (path === '/api/v1/vocabulary' && method === 'GET') {
      const search = url.searchParams.get('search')?.toLowerCase() ?? ''
      const pos = url.searchParams.get('pos') ?? ''
      const deckId = url.searchParams.get('deck_id') ?? ''
      const filtered = items.filter(
        (item) =>
          (!search ||
            item.display_form.toLowerCase().includes(search) ||
            item.lemma.toLowerCase().includes(search)) &&
          (!pos || item.part_of_speech === pos) &&
          (!deckId || item.deck_ids.includes(deckId)),
      )
      return Promise.resolve(
        jsonResponse({ items: filtered, total: filtered.length, page: 1, page_size: 20 }),
      )
    }

    if (path === '/api/v1/decks' && method === 'GET') {
      return Promise.resolve(jsonResponse({ items: decks }))
    }

    if (path === '/api/v1/decks' && method === 'POST') {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      const created = {
        id: `deck-${decks.length + 1}`,
        name: body.name,
        description: body.description ?? null,
        total_count: 0,
        due_count: 0,
        created_at: '2026-01-03T00:00:00Z',
        updated_at: '2026-01-03T00:00:00Z',
      }
      decks.push(created)
      return Promise.resolve(jsonResponse(created, 201))
    }

    const deckItemsMatch = path.match(/^\/api\/v1\/decks\/([^/]+)\/items$/)
    if (deckItemsMatch && method === 'POST') {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      const deckId = deckItemsMatch[1]
      for (const itemId of body.vocabulary_item_ids ?? []) {
        const item = items.find((candidate) => candidate.id === itemId)
        if (item && !item.deck_ids.includes(deckId)) item.deck_ids.push(deckId)
      }
      return Promise.resolve(new Response(null, { status: 204 }))
    }

    const removeDeckItemMatch = path.match(/^\/api\/v1\/decks\/([^/]+)\/items\/([^/]+)$/)
    if (removeDeckItemMatch && method === 'DELETE') {
      const [, deckId, itemId] = removeDeckItemMatch
      const item = items.find((candidate) => candidate.id === itemId)
      if (item) item.deck_ids = item.deck_ids.filter((id) => id !== deckId)
      return Promise.resolve(new Response(null, { status: 204 }))
    }

    const retryMatch = path.match(/^\/api\/v1\/vocabulary\/occurrences\/([^/]+)\/retry-translation$/)
    if (retryMatch && method === 'POST') {
      const occurrence = findOccurrence(retryMatch[1])
      if (!occurrence) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      occurrence.context_translation = 'It was a big challenge.'
      occurrence.needs_translation = false
      return Promise.resolve(jsonResponse(occurrence))
    }

    const occurrenceMatch = path.match(/^\/api\/v1\/vocabulary\/occurrences\/([^/]+)$/)
    if (occurrenceMatch && method === 'PATCH') {
      const occurrence = findOccurrence(occurrenceMatch[1])
      if (!occurrence) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      occurrence.context_translation = body.context_translation
      occurrence.needs_translation = body.context_translation === null
      return Promise.resolve(jsonResponse(occurrence))
    }

    const detailMatch = path.match(/^\/api\/v1\/vocabulary\/(.+)$/)
    if (detailMatch && method === 'GET') {
      const item = items.find((candidate) => candidate.id === detailMatch[1])
      if (!item) return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
      return Promise.resolve(jsonResponse({ ...item, occurrences: occurrencesOf(item) }))
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
    // Pre-filled from the deprecated fields for an item saved before `meanings` existed.
    expect(screen.getByRole('button', { name: 'Remove challenge' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('New meaning'), { target: { value: 'big challenge' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add meaning' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove challenge' }))
    fireEvent.click(screen.getByRole('button', { name: /Save changes/ }))

    // Back in view mode (the editor's own list row also says "big challenge").
    await screen.findByRole('button', { name: 'Edit' })
    await waitFor(() => expect(screen.getAllByText('big challenge').length).toBeGreaterThan(0))
    expect(screen.queryByText('challenge')).not.toBeInTheDocument()
  })

  it('reorders meanings and saves them in the new order', async () => {
    const fetchMock = mockFetch({
      items: [
        {
          ...ITEM_NOUN,
          meanings: [
            { text: 'challenge', source: 'machine' },
            { text: 'test', source: 'dictionary' },
            { text: 'provocation', source: 'dictionary' },
          ],
        },
      ],
    })
    vi.stubGlobal('fetch', fetchMock)
    renderVocabulary('/app/vocabulary?item=item-herausforderung')
    await screen.findByText('Plural: Herausforderungen')

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move provocation up' }))
    fireEvent.click(screen.getByRole('button', { name: /Save changes/ }))

    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/vocabulary/item-herausforderung') && init?.method === 'PATCH',
      )
      expect(patch).toBeDefined()
      expect(JSON.parse(String(patch![1]!.body)).meanings.map((m: { text: string }) => m.text)).toEqual(
        ['challenge', 'provocation', 'test'],
      )
    })
  })

  it('edits and retries the example translation, and chooses the card example', async () => {
    const line = 'Das war eine große Herausforderung.'
    const fetchMock = mockFetch({
      items: [ITEM_NOUN],
      occurrences: [
        {
          id: 'occ-new',
          article_id: 'article-2',
          start_offset: 0,
          end_offset: 15,
          context_sentence: 'Die Herausforderung bleibt.',
          context_line: 'Die Herausforderung bleibt.',
          context_translation: null,
          needs_translation: true,
          created_at: '2026-01-03T00:00:00Z',
        },
        {
          id: 'occ-old',
          article_id: 'article-1',
          start_offset: 19,
          end_offset: 34,
          context_sentence: line,
          context_line: line,
          context_translation: 'It was a challenge.',
          needs_translation: false,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    vi.stubGlobal('fetch', fetchMock)
    renderVocabulary('/app/vocabulary?item=item-herausforderung')
    await screen.findByText('Plural: Herausforderungen')

    // No example chosen yet: the first occurrence saved (the oldest) is the card example.
    const radios = screen.getAllByRole('radio', { name: 'Use on flashcard' })
    expect(radios[0]).not.toBeChecked()
    expect(radios[1]).toBeChecked()

    fireEvent.click(screen.getByRole('button', { name: 'Retry translation' }))
    expect(await screen.findByText('It was a big challenge.')).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit example translation' })[1])
    fireEvent.change(screen.getByLabelText('Example translation'), {
      target: { value: 'That was a big challenge.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save translation' }))
    await waitFor(() => expect(screen.getByText('That was a big challenge.')).toBeInTheDocument())

    fireEvent.click(screen.getAllByRole('radio', { name: 'Use on flashcard' })[0])
    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith('/vocabulary/item-herausforderung') &&
          init?.method === 'PATCH' &&
          String(init.body).includes('example_occurrence_id'),
      )
      expect(JSON.parse(String(patch![1]!.body))).toEqual({ example_occurrence_id: 'occ-new' })
    })
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

  it('filters the list by deck', async () => {
    const withDeckMembership = ALL_ITEMS.map((item) =>
      item.id === ITEM_NOUN.id ? { ...item, deck_ids: [DECK_FOOD.id] } : item,
    )
    vi.stubGlobal('fetch', mockFetch({ items: withDeckMembership, decks: [DECK_FOOD] }))
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.change(screen.getByLabelText('Filter by deck'), {
      target: { value: DECK_FOOD.id },
    })

    expect(await screen.findByText('Herausforderung')).toBeInTheDocument()
    expect(screen.queryByText('gewöhnen an')).not.toBeInTheDocument()
  })

  it('adds selected words to a deck', async () => {
    vi.stubGlobal('fetch', mockFetch({ decks: [DECK_FOOD] }))
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.click(screen.getByLabelText('Select Herausforderung'))
    expect(screen.getByText('1 selected')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add to deck' }))
    fireEvent.click(screen.getByRole('button', { name: DECK_FOOD.name }))

    expect(await screen.findByText('Added.')).toBeInTheDocument()
  })

  it('creates a new deck from the add-to-deck panel and adds the selection', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderVocabulary()
    await screen.findByText('Herausforderung')

    fireEvent.click(screen.getByLabelText('Select Herausforderung'))
    fireEvent.click(screen.getByRole('button', { name: 'Add to deck' }))

    fireEvent.change(screen.getByLabelText('New deck name'), {
      target: { value: 'Travel' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create & add/ }))

    expect(await screen.findByText('Added.')).toBeInTheDocument()
  })
})
