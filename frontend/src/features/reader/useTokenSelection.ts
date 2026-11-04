import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react'

import type { Token } from '../../types/analysis'

export interface TokenSelectionRange {
  startTokenIndex: number
  endTokenIndex: number
}

interface ClickOptions {
  shiftKey: boolean
}

// Roving tabindex + multi-word selection share one array: both only ever move between word
// tokens (not punctuation/whitespace), so there's a single notion of "the next/previous word"
// instead of two independent implementations of the same concept.
//
// Returned handlers are wrapped in useCallback and read mutable state through refs rather
// than closing over state values directly, so their identities stay stable across
// selection-driven re-renders — with thousands of tokens on a long article, that's what lets
// memoized token components actually skip re-rendering instead of all re-rendering on every
// click.
export function useTokenSelection(tokens: Token[]) {
  const wordTokenIndices = useMemo(
    () =>
      tokens.reduce<number[]>((acc, token, index) => {
        if (!token.is_punct && !token.is_space) acc.push(index)
        return acc
      }, []),
    [tokens],
  )

  const [activeTokenIndex, setActiveTokenIndex] = useState<number>(wordTokenIndices[0] ?? 0)
  const [selection, setSelection] = useState<TokenSelectionRange | null>(null)
  const [announcement, setAnnouncement] = useState('')

  const activeTokenIndexRef = useRef(activeTokenIndex)
  // Mirror state into a ref for callbacks to read without closing over a stale value — kept
  // in an effect rather than written during render, since refs shouldn't be mutated while
  // rendering.
  useLayoutEffect(() => {
    activeTokenIndexRef.current = activeTokenIndex
  }, [activeTokenIndex])
  const anchorIndexRef = useRef<number | null>(null)
  const isDraggingRef = useRef(false)

  const announceSelection = useCallback(
    (startIndex: number, endIndex: number) => {
      const words = tokens
        .slice(startIndex, endIndex + 1)
        .map((token) => token.text)
        .join(' ')
      setAnnouncement(`Selected: ${words}`)
    },
    [tokens],
  )

  const selectSingle = useCallback(
    (tokenIndex: number) => {
      activeTokenIndexRef.current = tokenIndex
      anchorIndexRef.current = tokenIndex
      setActiveTokenIndex(tokenIndex)
      setSelection({ startTokenIndex: tokenIndex, endTokenIndex: tokenIndex })
      announceSelection(tokenIndex, tokenIndex)
    },
    [announceSelection],
  )

  const extendSelection = useCallback(
    (tokenIndex: number) => {
      if (anchorIndexRef.current === null) {
        selectSingle(tokenIndex)
        return
      }
      activeTokenIndexRef.current = tokenIndex
      setActiveTokenIndex(tokenIndex)
      const start = Math.min(anchorIndexRef.current, tokenIndex)
      const end = Math.max(anchorIndexRef.current, tokenIndex)
      setSelection({ startTokenIndex: start, endTokenIndex: end })
      announceSelection(start, end)
    },
    [announceSelection, selectSingle],
  )

  const handleWordClick = useCallback(
    (tokenIndex: number, options: ClickOptions) => {
      if (options.shiftKey && anchorIndexRef.current !== null) {
        extendSelection(tokenIndex)
      } else {
        selectSingle(tokenIndex)
      }
    },
    [extendSelection, selectSingle],
  )

  const handleWordMouseDown = useCallback(
    (tokenIndex: number, options: ClickOptions) => {
      isDraggingRef.current = true
      handleWordClick(tokenIndex, options)
    },
    [handleWordClick],
  )

  const handleWordMouseEnter = useCallback(
    (tokenIndex: number) => {
      if (isDraggingRef.current) {
        extendSelection(tokenIndex)
      }
    },
    [extendSelection],
  )

  const endDrag = useCallback(() => {
    isDraggingRef.current = false
  }, [])

  const moveActive = useCallback(
    (direction: 1 | -1) => {
      const currentPosition = wordTokenIndices.indexOf(activeTokenIndexRef.current)
      const nextPosition = Math.min(
        Math.max(currentPosition + direction, 0),
        wordTokenIndices.length - 1,
      )
      const next = wordTokenIndices[nextPosition]
      activeTokenIndexRef.current = next
      setActiveTokenIndex(next)
    },
    [wordTokenIndices],
  )

  const handleKeyDown = useCallback(
    (event: { key: string; preventDefault: () => void }) => {
      if (event.key === 'ArrowRight') {
        moveActive(1)
        event.preventDefault()
      } else if (event.key === 'ArrowLeft') {
        moveActive(-1)
        event.preventDefault()
      } else if (event.key === 'Enter' || event.key === ' ') {
        selectSingle(activeTokenIndexRef.current)
        event.preventDefault()
      }
    },
    [moveActive, selectSingle],
  )

  const clearSelection = useCallback(() => {
    anchorIndexRef.current = null
    setSelection(null)
  }, [])

  return {
    wordTokenIndices,
    activeTokenIndex,
    selection,
    announcement,
    handleWordClick,
    handleWordMouseDown,
    handleWordMouseEnter,
    endDrag,
    handleKeyDown,
    clearSelection,
  }
}
