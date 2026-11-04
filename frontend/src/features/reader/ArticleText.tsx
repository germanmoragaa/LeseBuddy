import { forwardRef, memo } from 'react'
import type { KeyboardEvent, MouseEvent, MutableRefObject } from 'react'

import type { CodePointIndex } from '../../lib/textOffsets'
import type { SeparableVerb, Token } from '../../types/analysis'
import type { TokenSelectionRange } from './useTokenSelection'
import { Word } from './Word'

interface TokenWordProps {
  text: string
  tokenIndex: number
  isActive: boolean
  isSelected: boolean
  isSeparableVerbPart: boolean
  onClick: (tokenIndex: number, options: { shiftKey: boolean }) => void
  onMouseDown: (tokenIndex: number, options: { shiftKey: boolean }) => void
  onMouseEnter: (tokenIndex: number) => void
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
}

// Memoized so that selecting/moving focus only re-renders the handful of tokens whose props
// actually changed, not every token in the article — the reason this is a separate component
// rather than inlined in ArticleText's .map(). The DOM ref is accepted via forwardRef (not a
// named prop) and assigned by the caller (ArticleText), which is the component that actually
// owns the wordRefs collection.
const TokenWord = memo(
  forwardRef<HTMLButtonElement, TokenWordProps>(function TokenWord(
    { text, tokenIndex, isActive, isSelected, isSeparableVerbPart, onClick, onMouseDown, onMouseEnter, onKeyDown },
    ref,
  ) {
    return (
      <Word
        ref={ref}
        isActive={isActive}
        isSelected={isSelected}
        isSeparableVerbPart={isSeparableVerbPart}
        onMouseDown={(event: MouseEvent<HTMLButtonElement>) =>
          onMouseDown(tokenIndex, { shiftKey: event.shiftKey })
        }
        onMouseEnter={() => onMouseEnter(tokenIndex)}
        onClick={(event: MouseEvent<HTMLButtonElement>) =>
          onClick(tokenIndex, { shiftKey: event.shiftKey })
        }
        onKeyDown={onKeyDown}
      >
        {text}
      </Word>
    )
  }),
)

interface ArticleTextProps {
  originalText: string
  codePointIndex: CodePointIndex
  tokens: Token[]
  separableVerbs: SeparableVerb[]
  activeTokenIndex: number
  selection: TokenSelectionRange | null
  wordRefs: MutableRefObject<Record<number, HTMLButtonElement | null>>
  onWordClick: (tokenIndex: number, options: { shiftKey: boolean }) => void
  onWordMouseDown: (tokenIndex: number, options: { shiftKey: boolean }) => void
  onWordMouseEnter: (tokenIndex: number) => void
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void
}

export function ArticleText({
  originalText,
  codePointIndex,
  tokens,
  separableVerbs,
  activeTokenIndex,
  selection,
  wordRefs,
  onWordClick,
  onWordMouseDown,
  onWordMouseEnter,
  onKeyDown,
}: ArticleTextProps) {
  const separableVerbTokenIndices = new Set(
    separableVerbs.flatMap((verb) => [verb.verb_token_index, verb.particle_token_index]),
  )

  return (
    <div className="whitespace-pre-wrap font-serif text-[19px] leading-[1.82] text-[#343831]">
      {tokens.map((token, index) => {
        const text = codePointIndex.slice(originalText, token.start, token.end)
        const isWord = !token.is_punct && !token.is_space

        if (!isWord) {
          return (
            <span key={index}>
              {text}
              {token.whitespace_after}
            </span>
          )
        }

        const isSelected =
          selection !== null &&
          index >= selection.startTokenIndex &&
          index <= selection.endTokenIndex

        return (
          <span key={index}>
            <TokenWord
              ref={(element) => {
                wordRefs.current[index] = element
              }}
              text={text}
              tokenIndex={index}
              isActive={activeTokenIndex === index}
              isSelected={isSelected}
              isSeparableVerbPart={separableVerbTokenIndices.has(index)}
              onClick={onWordClick}
              onMouseDown={onWordMouseDown}
              onMouseEnter={onWordMouseEnter}
              onKeyDown={onKeyDown}
            />
            {token.whitespace_after}
          </span>
        )
      })}
    </div>
  )
}
