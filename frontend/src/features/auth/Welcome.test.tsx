import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { Welcome } from './Welcome'

describe('Welcome', () => {
  it('shows the tagline and links to create an account or log in', () => {
    render(
      <MemoryRouter>
        <Welcome />
      </MemoryRouter>,
    )

    expect(
      screen.getByText('Read authentic German. Understand more. Remember what you learn.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create account/i })).toHaveAttribute(
      'href',
      '/signup',
    )
    expect(screen.getByRole('link', { name: /log in/i })).toHaveAttribute('href', '/login')
  })
})
