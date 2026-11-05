import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleAnalysis, Token } from '../../types/analysis'
import type { VocabularyOccurrenceSummary } from '../../types/vocabulary'
import { Reader } from './Reader'

const ARTICLE_ID = 'test-article-1'
const ORIGINAL_TEXT = 'Ich rufe dich morgen an. 🐶 Gute Nacht.'

function makeToken(partial: Partial<Token> & Pick<Token, 'text' | 'start' | 'end'>): Token {
  return {
    whitespace_after: '',
    is_punct: false,
    is_space: false,
    lemma: partial.text,
    pos: 'X',
    morph: {},
    ...partial,
  }
}

const TOKENS: Token[] = [
  makeToken({ text: 'Ich', start: 0, end: 3, whitespace_after: ' ', lemma: 'ich', pos: 'PRON' }),
  makeToken({ text: 'rufe', start: 4, end: 8, whitespace_after: ' ', lemma: 'rufen', pos: 'VERB' }),
  makeToken({ text: 'dich', start: 9, end: 13, whitespace_after: ' ', lemma: 'dich', pos: 'PRON' }),
  makeToken({
    text: 'morgen',
    start: 14,
    end: 20,
    whitespace_after: ' ',
    lemma: 'morgen',
    pos: 'ADV',
  }),
  makeToken({ text: 'an', start: 21, end: 23, lemma: 'an', pos: 'ADP' }),
  makeToken({ text: '.', start: 23, end: 24, whitespace_after: ' ', is_punct: true, lemma: '--', pos: 'PUNCT' }),
  makeToken({
    text: '🐶',
    start: 25,
    end: 26,
    whitespace_after: ' ',
    is_punct: true,
    lemma: '🐶',
    pos: 'X',
  }),
  makeToken({ text: 'Gute', start: 27, end: 31, whitespace_after: ' ', lemma: 'gut', pos: 'ADJ' }),
  makeToken({
    text: 'Nacht',
    start: 32,
    end: 37,
    lemma: 'Nacht',
    pos: 'NOUN',
    morph: { Gender: 'Fem' },
  }),
  makeToken({ text: '.', start: 37, end: 38, is_punct: true, lemma: '--', pos: 'PUNCT' }),
]

const NACHT_START = 32
const NACHT_END = 37

const ANALYSIS: ArticleAnalysis = {
  analysis_version: 1,
  difficulty_estimate: null,
  tokens: TOKENS,
  sentences: [
    { start: 0, end: 24 },
    { start: 25, end: 38 },
  ],
  separable_verbs: [{ lemma: 'anrufen', verb_token_index: 1, particle_token_index: 4 }],
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

interface MockFetchOptions {
  occurrences?: VocabularyOccurrenceSummary[]
  dictionaryEntry?: Record<string, unknown> | null
  translateResponse?: Record<string, unknown>
  translateStatus?: number
  saveResponse?: Record<string, unknown>
}

function mockFetch(options: MockFetchOptions = {}) {
  const { occurrences = [], dictionaryEntry = null, translateStatus = 200, saveResponse } = options
  const translateResponse = options.translateResponse ?? {
    selection_translation: 'night',
    sentence_translation: null,
    quota_warning: null,
    source: 'machine_translation',
  }
  let translateCallCount = 0

  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const path = url.pathname

    if (path.endsWith(`/articles/${ARTICLE_ID}/analysis`)) {
      return Promise.resolve(jsonResponse(ANALYSIS))
    }
    if (path.endsWith(`/articles/${ARTICLE_ID}/vocabulary-occurrences`)) {
      return Promise.resolve(jsonResponse(occurrences))
    }
    if (path.endsWith(`/articles/${ARTICLE_ID}/dictionary`)) {
      const start = Number(url.searchParams.get('start'))
      const end = Number(url.searchParams.get('end'))
      return Promise.resolve(
        jsonResponse({
          lemma: 'Nacht',
          pos_detected: 'NOUN',
          is_separable_verb: false,
          entry: start === NACHT_START && end === NACHT_END ? dictionaryEntry : null,
        }),
      )
    }
    if (path.endsWith(`/articles/${ARTICLE_ID}/translate`)) {
      translateCallCount += 1
      if (translateStatus !== 200) {
        return Promise.resolve(
          jsonResponse(
            {
              detail: {
                code: 'translation_not_configured',
                message: "Translations aren't configured yet.",
              },
            },
            translateStatus,
          ),
        )
      }
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (body.include_sentence) {
        return Promise.resolve(
          jsonResponse({ ...translateResponse, sentence_translation: 'Good night.' }),
        )
      }
      return Promise.resolve(jsonResponse(translateResponse))
    }
    if (path.endsWith('/vocabulary') && init?.method === 'POST') {
      return Promise.resolve(
        jsonResponse(
          saveResponse ?? {
            item: {
              id: 'vocab-item-1',
              lemma: 'Nacht',
              display_form: 'Nacht',
              meaning: 'night',
              translation: 'night',
              part_of_speech: 'NOUN',
              grammar_metadata: { gender: 'Fem' },
              notes: null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            already_saved: false,
          },
          201,
        ),
      )
    }
    if (path.endsWith(`/articles/${ARTICLE_ID}`) && (init?.method ?? 'GET') === 'DELETE') {
      // A 204 response must have a null body — JSON.stringify(null) would produce the string
      // "null", which the Fetch spec rejects for a null-body status.
      return Promise.resolve(new Response(null, { status: 204 }))
    }
    if (path.endsWith(`/articles/${ARTICLE_ID}`)) {
      return Promise.resolve(
        jsonResponse({
          id: ARTICLE_ID,
          title: 'Test article',
          source_url: null,
          language: 'de',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          original_text: ORIGINAL_TEXT,
        }),
      )
    }
    return Promise.reject(new Error(`Unexpected fetch: ${rawUrl}`))
  })
}

function renderReader() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/reader/${ARTICLE_ID}`]}>
        <Routes>
          <Route path="/app/reader/:articleId" element={<Reader />} />
          <Route path="/app/reader" element={<div>Reading library</div>} />
          <Route path="/app" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...result, queryClient }
}

describe('Reader', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the article text exactly, including a word after an emoji', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()

    const main = await screen.findByRole('heading', { name: 'Test article' })
    const article = main.closest('main')
    expect(article).not.toBeNull()

    await screen.findByText('Nacht', { exact: false })
    expect(article!.textContent).toContain(ORIGINAL_TEXT)
  })

  it('navigates back to the reading library, not the dashboard', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    fireEvent.click(screen.getByRole('button', { name: 'Back to library' }))

    expect(await screen.findByText('Reading library')).toBeInTheDocument()
  })

  it('navigates home via the header "Home" link', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    fireEvent.click(screen.getByRole('button', { name: 'Home' }))

    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('deletes the article after confirmation, invalidates the cache, and navigates to the library', async () => {
    vi.stubGlobal('fetch', mockFetch())
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { queryClient } = renderReader()
    await screen.findByText('Nacht', { exact: false })
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const removeSpy = vi.spyOn(queryClient, 'removeQueries')

    fireEvent.click(screen.getByRole('button', { name: 'Delete article' }))

    expect(await screen.findByText('Reading library')).toBeInTheDocument()
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['articles'] })
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: ['article', ARTICLE_ID] })
  })

  it('does not delete the article when the confirmation is cancelled', async () => {
    vi.stubGlobal('fetch', mockFetch())
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    fireEvent.click(screen.getByRole('button', { name: 'Delete article' }))

    expect(screen.queryByText('Reading library')).not.toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Test article' })).toBeInTheDocument()
  })

  it('opens the detail panel with lemma and POS when a word is clicked', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    fireEvent.click(screen.getByRole('button', { name: 'dich' }))

    expect(await screen.findByRole('dialog', { name: 'Word detail' })).toBeInTheDocument()
    expect(screen.getByText('Lemma:').parentElement?.textContent).toContain('dich')
    expect(screen.getByText('Pronoun')).toBeInTheDocument()
  })

  it('highlights both parts of a separable verb and shows the combined infinitive', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    const verbButton = screen.getByRole('button', { name: 'rufe' })
    const particleButton = screen.getByRole('button', { name: 'an' })
    expect(verbButton.className).toContain('bg-surface-mint')
    expect(particleButton.className).toContain('bg-surface-mint')

    fireEvent.click(verbButton)

    expect(await screen.findByText('Verb (separable)')).toBeInTheDocument()
    expect(screen.getAllByText('anrufen').length).toBeGreaterThan(0)
  })

  it('snaps a shift+click selection to token boundaries, forward and reverse', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    fireEvent.click(screen.getByRole('button', { name: 'Ich' }))
    fireEvent.click(screen.getByRole('button', { name: 'dich' }), { shiftKey: true })

    expect(await screen.findByText('Expression · offsets 0–13')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'morgen' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ich' }), { shiftKey: true })

    expect(await screen.findByText('Expression · offsets 0–20')).toBeInTheDocument()
  })

  it('supports arrow-key navigation and Enter to select', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderReader()
    await screen.findByText('Nacht', { exact: false })

    const ichButton = screen.getByRole('button', { name: 'Ich' })
    const rufeButton = screen.getByRole('button', { name: 'rufe' })
    expect(ichButton).toHaveAttribute('tabindex', '0')
    expect(rufeButton).toHaveAttribute('tabindex', '-1')

    fireEvent.keyDown(ichButton, { key: 'ArrowRight' })
    expect(rufeButton).toHaveAttribute('tabindex', '0')
    expect(ichButton).toHaveAttribute('tabindex', '-1')

    fireEvent.keyDown(rufeButton, { key: 'Enter' })
    expect(await screen.findByRole('dialog', { name: 'Word detail' })).toBeInTheDocument()
    expect(screen.getByText('Verb (separable)')).toBeInTheDocument()
  })

  describe('word detail panel: dictionary and translation', () => {
    it('shows dictionary gender/plural/glosses and attribution when an entry is found', async () => {
      vi.stubGlobal(
        'fetch',
        mockFetch({
          dictionaryEntry: {
            pos: 'noun',
            gender: 'Fem',
            plural: 'Nächte',
            glosses: ['period of darkness between sunset and sunrise'],
            source_label: 'dictionary',
          },
        }),
      )
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))

      const pluralLabel = await screen.findByText('Plural:')
      expect(pluralLabel.parentElement?.textContent).toContain('Nächte')
      expect(
        screen.getByText('period of darkness between sunset and sunrise'),
      ).toBeInTheDocument()
      expect(screen.getAllByText(/Dictionary/).length).toBeGreaterThan(0)
      expect(screen.getByText(/Wiktionary/)).toBeInTheDocument()
    })

    it('shows "no dictionary entry" when none is found, and detected gender as a fallback', async () => {
      vi.stubGlobal('fetch', mockFetch({ dictionaryEntry: null }))
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))

      expect(await screen.findByText('No dictionary entry found for this word.')).toBeInTheDocument()
      expect(screen.getByText(/Detected/)).toBeInTheDocument()
    })

    it('shows the selection translation and loads a sentence translation on demand', async () => {
      vi.stubGlobal('fetch', mockFetch())
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))

      expect(await screen.findByText('night')).toBeInTheDocument()
      expect(screen.queryByText('Good night.')).not.toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: /Translate sentence/ }))

      expect(await screen.findByText('Good night.')).toBeInTheDocument()
    })

    it('stops auto-firing translation requests for the rest of the session after a not-configured error', async () => {
      const fetchMock = mockFetch({ translateStatus: 503 })
      vi.stubGlobal('fetch', fetchMock)
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))
      expect(await screen.findByText("Translations aren't configured yet.")).toBeInTheDocument()

      const callsAfterFirstError = fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes('/translate'),
      ).length
      expect(callsAfterFirstError).toBe(1)

      // Close and open the panel on a different word — translation must not be re-attempted.
      // Two elements share this aria-label (the backdrop and the icon button); click the icon.
      const closeButtons = screen.getAllByRole('button', { name: 'Close word detail' })
      fireEvent.click(closeButtons[closeButtons.length - 1])
      fireEvent.click(screen.getByRole('button', { name: 'dich' }))

      expect(await screen.findByText('Translations are unavailable right now.')).toBeInTheDocument()
      const callsAfterSecondOpen = fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes('/translate'),
      ).length
      expect(callsAfterSecondOpen).toBe(1)
    })
  })

  describe('word detail panel: save to vocabulary', () => {
    it('saves a word and switches to a Saved state with a link to the vocabulary item', async () => {
      vi.stubGlobal('fetch', mockFetch())
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))
      await screen.findByText('night')

      fireEvent.click(screen.getByRole('button', { name: /Save to vocabulary/ }))

      expect(await screen.findByRole('button', { name: /Saved/ })).toBeInTheDocument()
      const link = screen.getByRole('link', { name: 'View in vocabulary' })
      expect(link).toHaveAttribute('href', '/app/vocabulary?item=vocab-item-1')
    })

    it('shows an already-Saved state immediately for a selection that matches an existing occurrence', async () => {
      vi.stubGlobal(
        'fetch',
        mockFetch({
          occurrences: [
            { start_offset: NACHT_START, end_offset: NACHT_END, vocabulary_item_id: 'vocab-item-1' },
          ],
        }),
      )
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      fireEvent.click(screen.getByRole('button', { name: 'Nacht' }))

      expect(await screen.findByRole('button', { name: /Saved/ })).toBeInTheDocument()
    })

    it('subtly highlights words already saved to the vocabulary while reading', async () => {
      vi.stubGlobal(
        'fetch',
        mockFetch({
          occurrences: [
            { start_offset: NACHT_START, end_offset: NACHT_END, vocabulary_item_id: 'vocab-item-1' },
          ],
        }),
      )
      renderReader()
      await screen.findByText('Nacht', { exact: false })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Nacht' }).className).toContain(
          'bg-surface-lavender',
        )
      })
      expect(screen.getByRole('button', { name: 'dich' }).className).not.toContain(
        'bg-surface-lavender',
      )
    })
  })
})
