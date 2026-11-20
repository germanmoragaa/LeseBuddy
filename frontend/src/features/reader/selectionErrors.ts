import { ApiError, isApiErrorDetail } from '../../lib/api'

// Friendly copy for the API's 422 selection codes (backend/app/services/selection.py) — the
// panel never shows a raw validation error.
const SELECTION_ERROR_MESSAGES: Record<string, string> = {
  selection_spans_lines: 'Pick words from a single line of the song.',
  selection_not_in_lyric_line: "Section labels like [Hook] can't be looked up.",
  selection_spans_sentences: 'Pick words from a single sentence.',
  selection_misaligned: "This selection can't be looked up. Try selecting whole words.",
}

const FALLBACK_SELECTION_MESSAGE = "This selection can't be looked up. Try a smaller one."

export function isSelectionError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 422
}

// null when `error` isn't a selection (422) error at all.
export function selectionErrorMessage(error: unknown): string | null {
  if (!isSelectionError(error)) return null
  const detail = (error as ApiError).detail
  if (isApiErrorDetail(detail)) {
    return SELECTION_ERROR_MESSAGES[detail.code] ?? FALLBACK_SELECTION_MESSAGE
  }
  return FALLBACK_SELECTION_MESSAGE
}
