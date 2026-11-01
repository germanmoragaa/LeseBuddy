import { Bell, Menu, Search } from 'lucide-react'
import { useLocation } from 'react-router'

import { navItems } from '../app/navigation'

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { pathname } = useLocation()
  const title = navItems.find((item) => item.to === pathname)?.label ?? 'LeseBuddy'

  return (
    <header className="sticky top-0 z-10 flex h-[72px] items-center justify-between border-b border-line bg-surface/95 px-6 backdrop-blur">
      <div className="flex items-center gap-2.5 text-sm font-bold">
        <button
          type="button"
          aria-label="Open navigation"
          onClick={onMenuClick}
          className="grid h-10 w-10 place-items-center rounded-sm border border-line bg-white text-muted md:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
        >
          <Menu size={18} aria-hidden="true" />
        </button>
        <span>{title}</span>
      </div>
      <div className="flex items-center gap-2">
        <label className="hidden h-[38px] items-center gap-2 rounded-sm border border-line bg-white px-2.5 text-muted sm:flex has-[input:focus-visible]:outline has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-action">
          <Search size={17} aria-hidden="true" />
          <input
            placeholder="Search words, texts…"
            aria-label="Search"
            className="w-[180px] border-0 bg-transparent text-xs text-ink outline-none"
          />
        </label>
        <button
          type="button"
          aria-label="Notifications"
          className="relative grid h-10 w-10 place-items-center rounded-sm border border-line bg-white text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
        >
          <Bell size={19} aria-hidden="true" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full border border-white bg-action" />
        </button>
      </div>
    </header>
  )
}
