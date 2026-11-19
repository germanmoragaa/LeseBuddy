import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Header } from '../../components/Header'
import {
  jsonResponse,
  mockSongApi,
  NACHTLICHT,
  renderWithApp,
  resultsFor,
  SAMPLE_LYRICS,
  SOMMERREGEN,
} from './songTestUtils'

function savedArticle(id: string) {
  return jsonResponse(
    {
      id,
      kind: 'song',
      title: 'Nachtlicht',
      source_url: null,
      language: 'de',
      created_at: '2026-11-19T10:00:00Z',
      updated_at: '2026-11-19T10:00:00Z',
      word_count: 11,
      excerpt: null,
      last_opened_at: null,
      progress_percent: null,
      song: null,
      original_text: SAMPLE_LYRICS,
      reading_position: null,
    },
    201,
  )
}

function searchFor(value: string) {
  const input = screen.getByRole('combobox', { name: 'Search songs' })
  fireEvent.focus(input)
  fireEvent.change(input, { target: { value } })
  return input
}

async function openDialogFor(title: RegExp) {
  searchFor('Nacht')
  fireEvent.click(await screen.findByRole('option', { name: title }))
  return screen.getByRole('dialog', { name: 'Nachtlicht' })
}

describe('HeaderSongSearch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('replaces the old placeholder search in the app header', () => {
    vi.stubGlobal('fetch', mockSongApi({}))
    renderWithApp(<Header onMenuClick={() => {}} />)

    expect(screen.getByRole('combobox', { name: 'Search songs' })).toHaveAttribute(
      'placeholder',
      'Search songs to add…',
    )
    expect(screen.queryByPlaceholderText('Search words, texts…')).not.toBeInTheDocument()
  })

  it('shows debounced results in a dropdown', async () => {
    const fetchMock = mockSongApi({ search: resultsFor([NACHTLICHT, SOMMERREGEN]) })
    vi.stubGlobal('fetch', fetchMock)
    renderWithApp(<Header onMenuClick={() => {}} />)

    const input = searchFor('Na')
    fireEvent.change(input, { target: { value: 'Nacht' } })
    expect(fetchMock).not.toHaveBeenCalled()

    const listbox = await screen.findByRole('listbox', { name: 'Song results' })
    expect(within(listbox).getAllByRole('option')).toHaveLength(2)
    expect(within(listbox).getByText('Die Erfundenen · 2021')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-expanded', 'true')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('adds a song with pasted lyrics and opens it in the reader', async () => {
    const save = vi.fn(() => savedArticle('article-42'))
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([NACHTLICHT]), save }))
    const queryClient = renderWithApp(<Header onMenuClick={() => {}} />)
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const dialog = await openDialogFor(/Nachtlicht/)
    expect(within(dialog).getByRole('link', { name: /View on Genius/ })).toHaveAttribute(
      'href',
      NACHTLICHT.genius_url,
    )
    expect(within(dialog).getByText(/Lyrics stay private/)).toBeInTheDocument()
    const lyrics = within(dialog).getByLabelText('Lyrics')
    expect(lyrics).toHaveFocus()
    const submit = within(dialog).getByRole('button', { name: /Add song and start reading/ })
    expect(submit).toBeDisabled()

    fireEvent.change(lyrics, { target: { value: SAMPLE_LYRICS } })
    fireEvent.click(submit)

    expect(await screen.findByText('Reader for article-42')).toBeInTheDocument()
    // Only the id and the user's own lyrics are sent — never client-side metadata.
    expect(save).toHaveBeenCalledWith({ genius_song_id: 900001, lyrics_text: SAMPLE_LYRICS })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['articles'] })
  })

  it('offers to open the existing article when the song is already saved', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: resultsFor([NACHTLICHT]),
        save: () =>
          jsonResponse(
            {
              detail: {
                code: 'song_already_saved',
                message: 'This song is already in your library.',
                article_id: 'existing-7',
              },
            },
            409,
          ),
      }),
    )
    renderWithApp(<Header onMenuClick={() => {}} />)

    const dialog = await openDialogFor(/Nachtlicht/)
    fireEvent.change(within(dialog).getByLabelText('Lyrics'), {
      target: { value: SAMPLE_LYRICS },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: /Add song and start reading/ }))

    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent(/already in your library/)
    fireEvent.click(within(alert).getByRole('button', { name: 'Open it' }))

    expect(await screen.findByText('Reader for existing-7')).toBeInTheDocument()
  })

  it('shows a save error without leaving the dialog', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: resultsFor([NACHTLICHT]),
        save: () => jsonResponse({ detail: { code: 'songs_provider_error', message: 'x' } }, 502),
      }),
    )
    renderWithApp(<Header onMenuClick={() => {}} />)

    const dialog = await openDialogFor(/Nachtlicht/)
    fireEvent.change(within(dialog).getByLabelText('Lyrics'), {
      target: { value: SAMPLE_LYRICS },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: /Add song and start reading/ }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/Couldn't save the song/)
    expect(screen.getByRole('dialog', { name: 'Nachtlicht' })).toBeInTheDocument()
  })

  it('supports choosing a result with the keyboard', async () => {
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([NACHTLICHT, SOMMERREGEN]) }))
    renderWithApp(<Header onMenuClick={() => {}} />)

    const input = searchFor('Nacht')
    await screen.findByRole('listbox', { name: 'Song results' })
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    expect(screen.getByRole('option', { name: /Nachtlicht/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(screen.getByRole('dialog', { name: 'Nachtlicht' })).toBeInTheDocument()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('closes the dialog with Escape', async () => {
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([NACHTLICHT]) }))
    renderWithApp(<Header onMenuClick={() => {}} />)

    await openDialogFor(/Nachtlicht/)
    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('shows a not-configured message in the dropdown', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: () =>
          jsonResponse({ detail: { code: 'songs_not_configured', message: 'x' } }, 503),
      }),
    )
    renderWithApp(<Header onMenuClick={() => {}} />)

    searchFor('Nacht')

    expect(await screen.findByRole('alert')).toHaveTextContent(/Song search isn't set up yet/)
  })
})
