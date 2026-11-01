import { BarChart3, Bookmark, BookOpen, Home, Layers } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/reader', label: 'Reader', icon: BookOpen },
  { to: '/vocabulary', label: 'My vocabulary', icon: Bookmark },
  { to: '/flashcards', label: 'Flashcards', icon: Layers },
  { to: '/progress', label: 'Progress', icon: BarChart3 },
]
