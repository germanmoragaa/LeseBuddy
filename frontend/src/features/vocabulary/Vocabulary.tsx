import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { listVocabulary } from '../../lib/api'
import { VocabularyDetailDrawer } from './VocabularyDetailDrawer'

const POS_FILTER_OPTIONS = [
  { value: '', label: 'All word types' },
  { value: 'NOUN', label: 'Nouns' },
  { value: 'VERB', label: 'Verbs' },
  { value: 'ADJ', label: 'Adjectives' },
  { value: 'ADV', label: 'Adverbs' },
  { value: 'PHRASE', label: 'Expressions' },
]

const PAGE_SIZE = 20

export function Vocabulary() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('item')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [pos, setPos] = useState('')
  const [page, setPage] = useState(1)

  // Debounce typed search input rather than hitting the DB on every keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput)
      setPage(1)
    }, 300)
    return () => clearTimeout(timeout)
  }, [searchInput])

  const listQuery = useQuery({
    queryKey: ['vocabulary', search, pos, page],
    queryFn: () =>
      listVocabulary({
        search: search || undefined,
        pos: pos || undefined,
        page,
        pageSize: PAGE_SIZE,
      }),
  })

  const items = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const isUnfiltered = !search && !pos

  function openDrawer(id: string) {
    const next = new URLSearchParams(searchParams)
    next.set('item', id)
    setSearchParams(next)
  }

  function closeDrawer() {
    const next = new URLSearchParams(searchParams)
    next.delete('item')
    setSearchParams(next)
  }

  return (
    <div>
      <div className="mb-7 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your collection
          </span>
          <h1 className="my-1.5 text-[33px] tracking-tight">My vocabulary</h1>
          <p className="m-0 text-[13px] text-muted">
            Your personal collection of German words and expressions.
          </p>
        </div>
        <Button onClick={() => navigate('/app/reader/new')}>
          <Plus size={18} aria-hidden="true" /> Add a text
        </Button>
      </div>

      <div className="mb-4 flex min-h-[68px] flex-wrap items-center gap-2 rounded-md bg-brand px-5 py-3 text-[11px] text-[#c5d8ce]">
        <strong className="text-[26px] text-white">{total}</strong>
        <span>words and expressions</span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <label className="flex h-[42px] flex-1 basis-full items-center gap-2 rounded-sm border border-line bg-white px-2.5 text-muted sm:basis-auto">
          <Search size={17} aria-hidden="true" />
          <input
            placeholder="Search your vocabulary…"
            aria-label="Search your vocabulary"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            className="w-full border-0 bg-transparent text-xs text-ink outline-none"
          />
        </label>
        <select
          aria-label="Filter by word type"
          value={pos}
          onChange={(event) => {
            setPos(event.target.value)
            setPage(1)
          }}
          className="h-[42px] rounded-sm border border-line bg-white px-2.5 text-xs text-ink"
        >
          {POS_FILTER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <Card className="overflow-hidden">
        <div className="hidden min-h-[42px] grid-cols-[1.15fr_1.7fr_.9fr] items-center gap-4 border-b border-line bg-[#f7f6f2] px-5 text-[9px] font-bold uppercase tracking-wide text-muted md:grid">
          <span>Word or expression</span>
          <span>Meaning</span>
          <span>Saved</span>
        </div>

        {listQuery.isPending && <p className="px-5 py-10 text-center text-sm text-muted">Loading…</p>}
        {listQuery.isError && (
          <p className="px-5 py-10 text-center text-sm text-danger" role="alert">
            Couldn't load your vocabulary.
          </p>
        )}

        {listQuery.data && items.length === 0 && isUnfiltered && (
          <div className="flex flex-col items-center gap-3 px-5 py-14 text-center">
            <p className="text-sm text-muted">
              You haven't saved any words yet. Read a text and tap a word to save it here.
            </p>
            <Button onClick={() => navigate('/app/reader/new')}>
              <Plus size={18} aria-hidden="true" /> Add a text
            </Button>
          </div>
        )}
        {listQuery.data && items.length === 0 && !isUnfiltered && (
          <p className="px-5 py-10 text-center text-sm text-muted">No words match your search.</p>
        )}

        {items.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => openDrawer(item.id)}
            className="grid w-full min-h-[72px] grid-cols-1 items-center gap-4 border-b border-line px-5 py-3 text-left last:border-b-0 hover:bg-[#fdfdfb] md:grid-cols-[1.15fr_1.7fr_.9fr]"
          >
            <span>
              <strong className="block text-[13px]">{item.display_form}</strong>
              <small className="mt-1 block text-[9px] text-muted">{item.part_of_speech}</small>
            </span>
            <span>
              <strong className="block text-[11px]">{item.meaning ?? item.translation ?? '—'}</strong>
            </span>
            <span className="hidden md:block">
              <small className="block text-[9px] text-muted">
                {new Date(item.created_at).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                })}
              </small>
            </span>
          </button>
        ))}
      </Card>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button
            variant="icon"
            aria-label="Previous page"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </Button>
          <span className="text-[11px] text-muted">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="icon"
            aria-label="Next page"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page >= totalPages}
          >
            <ChevronRight size={18} aria-hidden="true" />
          </Button>
        </div>
      )}

      {selectedId && <VocabularyDetailDrawer itemId={selectedId} onClose={closeDrawer} />}
    </div>
  )
}
