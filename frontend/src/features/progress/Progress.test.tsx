import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AnalyticsActivity, AnalyticsOverview } from '../../types/analytics'
import { Progress } from './Progress'

const OVERVIEW: AnalyticsOverview = {
  words_saved: 50,
  words_mature: 10,
  words_saved_this_week: 5,
  reviews_today: 2,
  reviews_this_week: 20,
  due_now: 3,
  texts_opened_this_week: 1,
  streak: { current_days: 4, longest_days: 11, last_7_days: Array(7).fill(true) },
  recommendation: { type: 'review', reason: 'You have 3 cards due', article_id: null },
}

function makeDays(count: number, { reviews = 2, wordsSaved = 1 }: { reviews?: number; wordsSaved?: number } = {}) {
  return Array.from({ length: count }, (_, index) => {
    const date = new Date('2026-02-11T00:00:00Z')
    date.setDate(date.getDate() - (count - 1 - index))
    return {
      date: date.toISOString().slice(0, 10),
      reviews,
      words_saved: wordsSaved,
      cumulative_vocabulary: 10 + index,
    }
  })
}

function activityFor(days: number): AnalyticsActivity {
  return {
    days: makeDays(days),
    rating_counts: { again: 2, hard: 3, good: 10, easy: 5 },
    rating_percentages: { again: 10, hard: 15, good: 50, easy: 25 },
    retention_percent: 80,
  }
}

interface MockOptions {
  overview?: AnalyticsOverview
  emptyActivity?: boolean
}

function mockFetch({ overview = OVERVIEW, emptyActivity = false }: MockOptions = {}) {
  return vi.fn((url: string | URL | Request) => {
    const href = url.toString()
    if (href.includes('/analytics/overview')) {
      return Promise.resolve(new Response(JSON.stringify(overview), { status: 200 }))
    }
    if (href.includes('/analytics/activity')) {
      const requestUrl = new URL(href, 'http://localhost')
      const days = Number(requestUrl.searchParams.get('days') ?? '7')
      const body: AnalyticsActivity = emptyActivity
        ? {
            days: makeDays(days, { reviews: 0, wordsSaved: 0 }).map((day) => ({
              ...day,
              cumulative_vocabulary: 0,
            })),
            rating_counts: { again: 0, hard: 0, good: 0, easy: 0 },
            rating_percentages: { again: 0, hard: 0, good: 0, easy: 0 },
            retention_percent: null,
          }
        : activityFor(days)
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
    }
    return Promise.resolve(new Response(null, { status: 500 }))
  })
}

function renderProgress() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <Progress />
    </QueryClientProvider>,
  )
}

describe('Progress screen', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders real metrics for the default 7-day range', async () => {
    vi.stubGlobal('fetch', mockFetch())
    renderProgress()

    expect(await screen.findByText('Vocabulary saved')).toBeInTheDocument()
    // 7 days * 1 word/day from the mock activity series.
    expect(screen.getByText('7')).toBeInTheDocument()
    // 7 days * 2 reviews/day.
    expect(screen.getByText('14')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('4 days')).toBeInTheDocument()
  })

  it('switches range and refetches a longer activity series', async () => {
    const fetchMock = mockFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderProgress()
    await screen.findByText('Vocabulary saved')

    fireEvent.click(screen.getByRole('button', { name: '30 days' }))

    await waitFor(() => {
      const sawThirtyDays = fetchMock.mock.calls.some((call) => String(call[0]).includes('days=30'))
      expect(sawThirtyDays).toBe(true)
    })
    // 30 days * 1 word/day.
    expect(await screen.findByText('30')).toBeInTheDocument()
  })

  it('shows an empty state for a brand-new user with no activity', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        overview: { ...OVERVIEW, words_saved: 0 },
        emptyActivity: true,
      }),
    )
    renderProgress()

    expect(
      await screen.findByText(/haven't saved any words or done any reviews yet/i),
    ).toBeInTheDocument()
    expect(screen.queryByText('Vocabulary saved')).not.toBeInTheDocument()
  })
})
