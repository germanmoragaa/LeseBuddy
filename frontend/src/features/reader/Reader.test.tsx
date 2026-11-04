import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ArticleAnalysis, Token } from '../../types/analysis'
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
  makeToken({ text: 'Nacht', start: 32, end: 37, lemma: 'Nacht', pos: 'NOUN' }),
  makeToken({ text: '.', start: 37, end: 38, is_punct: true, lemma: '--', pos: 'PUNCT' }),
]

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

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200 })
}

function mockFetch() {
  return vi.fn((url: string) => {
    if (url.endsWith(`/articles/${ARTICLE_ID}/analysis`)) {
      return Promise.resolve(jsonResponse(ANALYSIS))
    }
    if (url.endsWith(`/articles/${ARTICLE_ID}`)) {
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
    return Promise.reject(new Error(`Unexpected fetch: ${url}`))
  })
}

function renderReader() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/reader/${ARTICLE_ID}`]}>
        <Routes>
          <Route path="/app/reader/:articleId" element={<Reader />} />
          <Route path="/app" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
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
})
