import { useState } from 'react'
import { Outlet } from 'react-router'

import { Header } from '../components/Header'
import { Sidebar } from '../components/Sidebar'

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="min-h-screen md:ml-60">
        <Header onMenuClick={() => setMobileNavOpen(true)} />
        <main className="mx-auto max-w-[1320px] px-6 py-9">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
