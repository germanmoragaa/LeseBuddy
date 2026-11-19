import { useEffect, useState } from 'react'

// Returns `value` only after it has stopped changing for `delayMs` — e.g. so a search input
// fires one request per typing pause instead of one per keystroke.
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timeout = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timeout)
  }, [value, delayMs])

  return debounced
}
