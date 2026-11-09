export function formatNextDue(nextDueAt: string | null): string {
  if (!nextDueAt) return "You're all caught up!"
  const date = new Date(nextDueAt)
  if (date.getTime() <= Date.now()) return 'More cards are ready now'
  return `Next review ${date.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  })}`
}
