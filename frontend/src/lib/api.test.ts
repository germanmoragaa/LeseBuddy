import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch } from './api'

// Simulates a backend that never responds (e.g. a request stuck behind a database lock) —
// the promise only ever settles via the abort signal `request()` attaches, exactly like a
// real hung fetch() would behave against AbortSignal.timeout().
function mockHangingFetch() {
  return vi.fn((_url: string, init?: RequestInit) => {
    return new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => {
        reject(init.signal!.reason)
      })
    })
  })
}

describe('request timeout', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('turns a hung request into an ApiError instead of waiting forever', async () => {
    vi.stubGlobal('fetch', mockHangingFetch())

    let caught: unknown
    try {
      await apiFetch('/reviews/due', 50)
    } catch (error) {
      caught = error
    }

    expect(caught).toBeInstanceOf(ApiError)
    expect((caught as ApiError).status).toBe(0)
    expect((caught as ApiError).message).toContain('timed out')
  })

  it('does not time out a request that resolves well within the budget', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }))),
    )

    await expect(apiFetch('/reviews/due', 1000)).resolves.toEqual({ items: [] })
  })
})
