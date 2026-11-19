import { QueryClient } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createElement } from 'react'
import type { ReactElement } from 'react'
import { vi } from 'vitest'

import type { SongSearchResult } from '../../types/song'
import { SongTestApp } from './SongTestApp'

// Invented songs only — never real titles, artists or lyrics (ADR 0006).
export const NACHTLICHT: SongSearchResult = {
  genius_id: 900001,
  title: 'Nachtlicht',
  primary_artist: 'Die Erfundenen',
  thumbnail_url: 'https://images.example.test/nachtlicht-300x300.jpg',
  cover_url: 'https://images.example.test/nachtlicht-1000x1000.jpg',
  genius_url: 'https://genius.example.test/die-erfundenen-nachtlicht',
  release_date_display: 'May 14, 2021',
  release_year: 2021,
  language: 'de',
}

export const SOMMERREGEN: SongSearchResult = {
  genius_id: 900004,
  title: 'Sommerregen',
  primary_artist: 'Kapelle Ohnenamen',
  thumbnail_url: null,
  cover_url: null,
  genius_url: null,
  release_date_display: null,
  release_year: null,
  language: null,
}

export const SAMPLE_LYRICS = "[Hook]\nIch lauf' durch die Nacht\nUnd die Stadt ist noch wach"

export function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

interface SongApiMock {
  search?: (query: string) => Response
  save?: (body: { genius_song_id: number; lyrics_text: string }) => Response
}

export function mockSongApi({ search, save }: SongApiMock) {
  return vi.fn((rawUrl: string, init?: RequestInit) => {
    const url = new URL(rawUrl, 'http://localhost')
    const method = init?.method ?? 'GET'
    if (url.pathname === '/api/v1/songs/search' && method === 'GET' && search) {
      return Promise.resolve(search(url.searchParams.get('q') ?? ''))
    }
    if (url.pathname === '/api/v1/songs' && method === 'POST' && save) {
      return Promise.resolve(save(JSON.parse(String(init?.body))))
    }
    return Promise.reject(new Error(`Unexpected fetch: ${method} ${rawUrl}`))
  })
}

export const resultsFor = (results: SongSearchResult[]) => (query: string) =>
  jsonResponse({ query, results })

export function renderWithApp(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(createElement(SongTestApp, { ui, queryClient }))
  return queryClient
}
