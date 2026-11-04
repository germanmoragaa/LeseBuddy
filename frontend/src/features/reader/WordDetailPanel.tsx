import { Bookmark, X } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { Button } from '../../components/Button'
import type { CodePointIndex } from '../../lib/textOffsets'
import type { SeparableVerb, Token } from '../../types/analysis'
import { formatMorph, posLabel } from './grammarLabels'
import type { TokenSelectionRange } from './useTokenSelection'

interface WordDetailPanelProps {
  originalText: string
  codePointIndex: CodePointIndex
  tokens: Token[]
  selection: TokenSelectionRange
  separableVerbs: SeparableVerb[]
  onClose: () => void
}

export function WordDetailPanel({
  originalText,
  codePointIndex,
  tokens,
  selection,
  separableVerbs,
  onClose,
}: WordDetailPanelProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Move focus into the panel on open. Returning focus to the word that triggered it is the
  // caller's responsibility (Reader.tsx's onClose) — this component doesn't know which
  // element opened it.
  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  const { startTokenIndex, endTokenIndex } = selection
  const isSingleWord = startTokenIndex === endTokenIndex
  const surfaceText = codePointIndex.slice(
    originalText,
    tokens[startTokenIndex].start,
    tokens[endTokenIndex].end,
  )

  const activeToken = tokens[startTokenIndex]
  const separableVerb = isSingleWord
    ? separableVerbs.find(
        (verb) =>
          verb.verb_token_index === startTokenIndex || verb.particle_token_index === startTokenIndex,
      )
    : undefined
  const morphLine = isSingleWord ? formatMorph(activeToken.morph) : null

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close word detail"
        onClick={onClose}
        className="absolute inset-0 w-full border-0 bg-black/30"
      />
      <aside
        role="dialog"
        aria-label="Word detail"
        className="fixed inset-x-0 bottom-0 z-50 max-h-[70vh] overflow-y-auto rounded-t-2xl border-t border-line bg-white p-6 shadow-[0_-20px_60px_rgb(25_40_31_/_0.14)] sm:inset-y-0 sm:right-0 sm:left-auto sm:bottom-auto sm:max-h-none sm:w-full sm:max-w-[400px] sm:rounded-t-none sm:border-t-0 sm:border-l sm:shadow-[-20px_0_60px_rgb(25_40_31_/_0.14)]"
      >
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
            Word detail
          </span>
          <Button ref={closeButtonRef} variant="icon" aria-label="Close word detail" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        <div className="border-b border-line py-7">
          <h2 className="mb-1 mt-2.5 text-[28px] tracking-tight">{surfaceText}</h2>

          {isSingleWord ? (
            <>
              <p className="text-muted">
                Lemma: <span className="text-ink">{separableVerb?.lemma ?? activeToken.lemma}</span>
              </p>
              <p className="mt-1 text-muted">
                {separableVerb ? 'Verb (separable)' : posLabel(activeToken.pos)}
              </p>
              {morphLine && <p className="mt-1 text-muted">{morphLine}</p>}
              {separableVerb && (
                <p className="mt-3 rounded-sm bg-surface-mint px-3 py-2 text-[11px] text-brand">
                  Separable verb: both highlighted parts combine into{' '}
                  <strong>{separableVerb.lemma}</strong>.
                </p>
              )}
            </>
          ) : (
            <p className="text-muted">
              Expression · offsets {tokens[startTokenIndex].start}–{tokens[endTokenIndex].end}
            </p>
          )}
        </div>

        <div className="py-5">
          <Button className="w-full" aria-disabled={true} onClick={() => {}}>
            <Bookmark size={16} aria-hidden="true" /> Save to vocabulary
          </Button>
          <p className="mt-2 text-center text-[10px] text-muted">
            Coming soon — vocabulary saving isn't available yet.
          </p>
        </div>
      </aside>
    </div>
  )
}
