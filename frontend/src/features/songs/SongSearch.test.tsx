import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SongSearch } from './SongSearch'
import {
  jsonResponse,
  mockSongApi,
  NACHTLICHT,
  renderWithApp,
  resultsFor,
  SOMMERREGEN,
} from './songTestUtils'
import { SONG_SEARCH_DEBOUNCE_MS } from './useSongSearch'

function type(value: string) {
  fireEvent.change(screen.getByRole('searchbox', { name: /Search by title or artist/ }), {
    target: { value },
  })
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

describe('SongSearch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('debounces typing into a single search and renders the results', async () => {
    const fetchMock = mockSongApi({ search: resultsFor([NACHTLICHT, SOMMERREGEN]) })
    vi.stubGlobal('fetch', fetchMock)
    renderWithApp(<SongSearch />)

    type('Na')
    type('Nach')
    type('Nacht')
    expect(fetchMock).not.toHaveBeenCalled()

    const list = await screen.findByRole('list', { name: 'Song results' })
    expect(within(list).getByText('Nachtlicht')).toBeInTheDocument()
    expect(within(list).getByText('Die Erfundenen · 2021')).toBeInTheDocument()
    // No year known -> artist only.
    expect(within(list).getByText('Kapelle Ohnenamen')).toBeInTheDocument()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const calledUrl = new URL(String(fetchMock.mock.calls[0][0]), 'http://localhost')
    expect(calledUrl.searchParams.get('q')).toBe('Nacht')
  })

  it('renders hotlinked thumbnails lazily without a referrer', async () => {
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([NACHTLICHT]) }))
    renderWithApp(<SongSearch />)

    type('Nacht')

    const list = await screen.findByRole('list', { name: 'Song results' })
    const img = list.querySelector('img')
    expect(img).toHaveAttribute('src', NACHTLICHT.thumbnail_url)
    expect(img).toHaveAttribute('loading', 'lazy')
    expect(img).toHaveAttribute('referrerpolicy', 'no-referrer')
  })

  it('does not search for queries shorter than two characters', async () => {
    const fetchMock = mockSongApi({ search: resultsFor([NACHTLICHT]) })
    vi.stubGlobal('fetch', fetchMock)
    renderWithApp(<SongSearch />)

    type(' N ')
    await wait(SONG_SEARCH_DEBOUNCE_MS + 100)

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('list', { name: 'Song results' })).not.toBeInTheDocument()
  })

  it('opens the add-song dialog when a result is clicked', async () => {
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([NACHTLICHT, SOMMERREGEN]) }))
    renderWithApp(<SongSearch />)

    type('Nacht')
    fireEvent.click(await screen.findByRole('button', { name: /Nachtlicht/ }))

    const dialog = screen.getByRole('dialog', { name: 'Nachtlicht' })
    expect(within(dialog).getByLabelText('Lyrics')).toBeInTheDocument()
    // The full-size cover in the dialog, not the thumbnail.
    expect(dialog.querySelector('img')).toHaveAttribute('src', NACHTLICHT.cover_url)
  })

  it('shows an empty state when nothing matches', async () => {
    vi.stubGlobal('fetch', mockSongApi({ search: resultsFor([]) }))
    renderWithApp(<SongSearch />)

    type('zzzz')

    expect(await screen.findByText('No songs found for “zzzz”.')).toBeInTheDocument()
  })

  it('shows a not-configured message when the backend has no Genius token', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: () =>
          jsonResponse({ detail: { code: 'songs_not_configured', message: 'x' } }, 503),
      }),
    )
    renderWithApp(<SongSearch />)

    type('Nacht')

    expect(await screen.findByRole('alert')).toHaveTextContent(/Song search isn't set up yet/)
  })

  it('shows a rate-limit message on 429', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: () =>
          jsonResponse(
            { detail: { code: 'songs_rate_limited', message: 'x', retry_after: 12 } },
            429,
          ),
      }),
    )
    renderWithApp(<SongSearch />)

    type('Nacht')

    expect(await screen.findByRole('alert')).toHaveTextContent(/searching very quickly/)
  })

  it('shows a generic error when the provider fails', async () => {
    vi.stubGlobal(
      'fetch',
      mockSongApi({
        search: () => jsonResponse({ detail: { code: 'songs_provider_error', message: 'x' } }, 502),
      }),
    )
    renderWithApp(<SongSearch />)

    type('Nacht')

    expect(await screen.findByRole('alert')).toHaveTextContent(/Couldn't reach song search/)
  })
})
