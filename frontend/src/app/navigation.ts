import { BarChart3, Bookmark, BookOpen, Home, Layers } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export const navItems: NavItem[] = [
  { to: '/app', label: 'Home', icon: Home },
  { to: '/app/reader/new', label: 'Reader', icon: BookOpen },
  { to: '/app/vocabulary', label: 'My vocabulary', icon: Bookmark },
  { to: '/app/flashcards', label: 'Flashcards', icon: Layers },
  { to: '/app/progress', label: 'Progress', icon: BarChart3 },
]
