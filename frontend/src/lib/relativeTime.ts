const MINUTE_MS = 60_000
const HOUR_MS = 60 * MINUTE_MS
const DAY_MS = 24 * HOUR_MS
const WEEK_MS = 7 * DAY_MS

// `now` is a parameter (not `new Date()` inline) so tests can pin it instead of racing the
// clock.
export function formatRelativeTime(value: string, now: Date = new Date()): string {
  const diffMs = now.getTime() - new Date(value).getTime()

  if (diffMs < MINUTE_MS) return 'just now'
  if (diffMs < HOUR_MS) {
    const minutes = Math.floor(diffMs / MINUTE_MS)
    return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  }
  if (diffMs < DAY_MS) {
    const hours = Math.floor(diffMs / HOUR_MS)
    return `${hours} hour${hours === 1 ? '' : 's'} ago`
  }
  if (diffMs < WEEK_MS) {
    const days = Math.floor(diffMs / DAY_MS)
    return `${days} day${days === 1 ? '' : 's'} ago`
  }
  return new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
