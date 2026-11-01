export function getGermanGreeting(date: Date): string {
  const hour = date.getHours()

  if (hour < 12) return 'Guten Morgen'
  if (hour < 18) return 'Guten Tag'
  return 'Guten Abend'
}
