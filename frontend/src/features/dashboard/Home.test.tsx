import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import {
  mockContinueReading,
  mockDashboardStats,
  mockRecentArticles,
  mockUser,
} from '../../mocks/dashboard'
import { Home } from './Home'

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )
}

describe('Home dashboard', () => {
  it('greets the user by first name', () => {
    renderHome()

    const firstName = mockUser.name.split(' ')[0]
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(firstName)
  })

  it('renders the dashboard stats from mock data', () => {
    renderHome()

    expect(screen.getByText(String(mockDashboardStats.wordsLearned))).toBeInTheDocument()
    expect(screen.getByText(String(mockDashboardStats.reviewsCompletedThisWeek))).toBeInTheDocument()
    expect(screen.getByText(`${mockDashboardStats.readingHoursThisWeek}h`)).toBeInTheDocument()
  })

  it('renders the continue-reading article and recent reading list', () => {
    renderHome()

    // The "continue reading" article is also the most recent one in the library list,
    // so its title legitimately appears twice on the page.
    expect(screen.getAllByText(mockContinueReading.title).length).toBeGreaterThanOrEqual(2)
    for (const article of mockRecentArticles.slice(1)) {
      expect(screen.getByText(article.title)).toBeInTheDocument()
    }
  })
})
