import { Calendar, Filter, MoreHorizontal, Plus, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { mockVocabularyItems } from '../../mocks/vocabulary'
import { StatusBadge } from './StatusBadge'
import { VocabularyDetailDrawer } from './VocabularyDetailDrawer'

export function Vocabulary() {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const items = useMemo(
    () =>
      mockVocabularyItems.filter((item) => item.word.toLowerCase().includes(query.toLowerCase())),
    [query],
  )
  const selectedItem = mockVocabularyItems.find((item) => item.id === selectedId)
  const dueCount = mockVocabularyItems.filter(
    (item) => item.status === 'due-soon' || item.status === 'review',
  ).length

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
        <Button>
          <Plus size={18} aria-hidden="true" /> Add a word
        </Button>
      </div>

      <div className="mb-4 flex min-h-[68px] flex-wrap items-center gap-2 rounded-md bg-brand px-5 py-3 text-[11px] text-[#c5d8ce]">
        <strong className="text-[26px] text-white">{mockVocabularyItems.length}</strong>
        <span>words and expressions</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="h-6 w-px bg-white/20" />
          <b className="text-accent">{dueCount}</b> due for review
        </span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <label className="flex h-[42px] flex-1 basis-full items-center gap-2 rounded-sm border border-line bg-white px-2.5 text-muted sm:basis-auto">
          <Search size={17} aria-hidden="true" />
          <input
            placeholder="Search your vocabulary…"
            aria-label="Search your vocabulary"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full border-0 bg-transparent text-xs text-ink outline-none"
          />
        </label>
        <Button variant="secondary">
          <Filter size={16} aria-hidden="true" /> All word types ⌄
        </Button>
        <Button variant="secondary">
          <Calendar size={16} aria-hidden="true" /> Review status ⌄
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div className="hidden min-h-[42px] grid-cols-[1.15fr_1.7fr_.65fr_.9fr_25px] items-center gap-4 border-b border-line bg-[#f7f6f2] px-5 text-[9px] font-bold uppercase tracking-wide text-muted md:grid">
          <span>Word or expression</span>
          <span>Meaning &amp; context</span>
          <span>Status</span>
          <span>Source</span>
          <span />
        </div>
        {items.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => setSelectedId(item.id)}
            className="grid w-full min-h-[83px] grid-cols-2 items-center gap-4 border-b border-line px-5 py-3 text-left last:border-b-0 hover:bg-[#fdfdfb] md:grid-cols-[1.15fr_1.7fr_.65fr_.9fr_25px]"
          >
            <span>
              <strong className="block text-[13px]">{item.word}</strong>
              <small className="mt-1 block text-[9px] text-muted">{item.wordType}</small>
            </span>
            <span>
              <strong className="block text-[11px]">{item.meaning}</strong>
              <small className="mt-1 block text-[9px] text-muted">{item.exampleSentence}</small>
            </span>
            <span>
              <StatusBadge status={item.status} />
            </span>
            <span className="hidden md:block">
              <small className="block text-[9px] text-muted">{item.sourceTitle}</small>
              <em className="not-italic text-[9px] text-muted">{item.sourceDateLabel}</em>
            </span>
            <MoreHorizontal size={18} aria-hidden="true" className="hidden text-muted md:block" />
          </button>
        ))}
        {items.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No words match “{query}”.
          </p>
        )}
      </Card>

      {selectedItem && (
        <VocabularyDetailDrawer item={selectedItem} onClose={() => setSelectedId(null)} />
      )}
    </div>
  )
}
