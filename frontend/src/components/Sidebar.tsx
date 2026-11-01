import { MoreHorizontal, Sparkles, X } from 'lucide-react'
import { NavLink } from 'react-router'

import { navItems } from '../app/navigation'
import { mockDueFlashcardsCount, mockStreak, mockUser } from '../mocks/dashboard'
import { ApiStatus } from './ApiStatus'
import { Logo } from './Logo'

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-20 bg-black/30 md:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-60 -translate-x-full flex-col border-r border-line bg-[#fdfcf9] px-5 pb-5 pt-7 transition-transform duration-200 ease-out md:translate-x-0 ${
          open ? 'translate-x-0' : ''
        }`}
      >
        <div className="flex items-center justify-between">
          <Logo />
          <button
            type="button"
            aria-label="Close navigation"
            onClick={onClose}
            className="grid h-10 w-10 place-items-center rounded-sm border border-line bg-white text-muted md:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <p className="ml-[46px] mt-3 mb-6 text-[8px] font-bold uppercase tracking-[0.13em] text-muted">
          Your reading companion
        </p>

        <nav aria-label="Primary navigation" className="grid gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={onClose}
                className={({ isActive }) =>
                  `relative flex min-h-11 items-center gap-3 rounded-[11px] px-3 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action ${
                    isActive
                      ? 'bg-surface-mint text-brand hover:bg-surface-mint-strong'
                      : 'text-[#676c65] hover:bg-[#f3f1ec] hover:text-ink'
                  }`
                }
              >
                <Icon size={19} aria-hidden="true" />
                <span>{item.label}</span>
                {item.to === '/flashcards' && (
                  <span className="ml-auto grid h-[22px] min-w-[22px] place-items-center rounded-[11px] border border-surface-mint-strong bg-white px-1.5 text-[11px] text-brand">
                    {mockDueFlashcardsCount}
                  </span>
                )}
              </NavLink>
            )
          })}
        </nav>

        <div className="mt-auto rounded-md border border-[#eee1a9] bg-accent-soft p-4">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="grid h-[27px] w-[27px] place-items-center rounded-[9px] bg-accent text-[#8b6f10]">
              <Sparkles size={16} aria-hidden="true" />
            </span>
            <strong>{mockStreak.days}-day streak</strong>
          </div>
          <div className="my-3.5 flex justify-between">
            {DAY_LABELS.map((day, index) => (
              <span
                key={`${day}-${index}`}
                className={`grid h-[21px] w-[21px] place-items-center rounded-full border text-[9px] font-bold ${
                  mockStreak.completedToday[index]
                    ? 'border-action bg-action text-white'
                    : 'border-[#e3dac0] text-[#a8a28b]'
                }`}
              >
                {day}
              </span>
            ))}
          </div>
          <p className="m-0 text-[11px] text-[#786f51]">You're building a habit!</p>
        </div>

        <div className="mt-4 grid grid-cols-[36px_1fr_auto] items-center gap-2.5 border-t border-line pt-3.5">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-surface-mint-strong text-[11px] font-bold text-brand">
            {mockUser.initials}
          </span>
          <span>
            <strong className="block text-xs">{mockUser.name}</strong>
            <small className="mt-0.5 block text-[10px] text-muted">{mockUser.level}</small>
          </span>
          <button
            type="button"
            aria-label="More account options"
            className="rounded-sm text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
          >
            <MoreHorizontal size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="mt-2">
          <ApiStatus />
        </div>
      </aside>
    </>
  )
}
