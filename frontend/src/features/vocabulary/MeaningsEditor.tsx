import { ArrowDown, ArrowUp, Plus, X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../components/Button'
import type { Meaning } from '../../types/vocabulary'

interface MeaningsEditorProps {
  meanings: Meaning[]
  onChange: (meanings: Meaning[]) => void
}

// Ordered list editor: the first meaning is the one the flashcard emphasizes. Adding a text
// that's already there (case-insensitively) is a no-op, matching the backend's dedup.
export function MeaningsEditor({ meanings, onChange }: MeaningsEditorProps) {
  const [draft, setDraft] = useState('')

  function move(index: number, direction: -1 | 1) {
    const target = index + direction
    if (target < 0 || target >= meanings.length) return
    const next = [...meanings]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  function remove(index: number) {
    onChange(meanings.filter((_, position) => position !== index))
  }

  function add() {
    const text = draft.trim()
    if (!text) return
    if (!meanings.some((meaning) => meaning.text.toLowerCase() === text.toLowerCase())) {
      // A meaning the user typed themselves is their own contextual one, not dictionary data.
      onChange([...meanings, { text, source: 'machine' }])
    }
    setDraft('')
  }

  return (
    <div className="flex flex-col gap-1.5">
      <ol aria-label="Meanings" className="m-0 flex list-none flex-col gap-1.5 p-0">
        {meanings.map((meaning, index) => (
          <li
            key={`${meaning.text}-${index}`}
            className="flex items-center gap-1.5 rounded-sm border border-line px-2.5 py-1.5 text-[12px]"
          >
            <span className="min-w-0 flex-1 truncate">{meaning.text}</span>
            <button
              type="button"
              aria-label={`Move ${meaning.text} up`}
              onClick={() => move(index, -1)}
              disabled={index === 0}
              className="text-muted disabled:opacity-30"
            >
              <ArrowUp size={14} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label={`Move ${meaning.text} down`}
              onClick={() => move(index, 1)}
              disabled={index === meanings.length - 1}
              className="text-muted disabled:opacity-30"
            >
              <ArrowDown size={14} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label={`Remove ${meaning.text}`}
              onClick={() => remove(index)}
              className="text-danger"
            >
              <X size={14} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ol>
      <div className="flex gap-1.5">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault()
              add()
            }
          }}
          placeholder="Add a meaning"
          aria-label="New meaning"
          className="min-w-0 flex-1 rounded-sm border border-line px-2.5 py-2 text-[12px]"
        />
        <Button variant="secondary" onClick={add} disabled={!draft.trim()} aria-label="Add meaning">
          <Plus size={14} aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
