import { Plus, Play } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { useCurrentUser } from '../../hooks/useCurrentUser'
import { getGermanGreeting } from '../../lib/greeting'

const onBrandButton =
  'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-sm border border-transparent px-4 text-[13px] font-bold transition hover:-translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white'

export function WelcomeBanner() {
  const navigate = useNavigate()
  const { data: currentUser } = useCurrentUser()
  const [now] = useState(() => new Date())
  const username = currentUser?.username ?? ''
  const weekday = now.toLocaleDateString('en-GB', { weekday: 'long' })
  const dayAndMonth = now.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })
  const dateLabel = `${weekday}, ${dayAndMonth}`

  return (
    <section className="relative flex min-h-56 items-center justify-between overflow-hidden rounded-lg bg-brand px-9 py-8 text-white">
      <div className="relative z-10">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[#b9d0c4]">
          {dateLabel}
        </span>
        <h1 className="mb-1 mt-2 text-[clamp(28px,3vw,38px)] leading-tight tracking-tight">
          {getGermanGreeting(now)}, {username}{' '}
          <span className="inline-block rotate-[-20deg] text-accent">↗</span>
        </h1>
        <p className="mb-6 text-sm text-[#cee0d5]">Ready to discover something new in German?</p>
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            onClick={() => navigate('/app/reader')}
            className={`${onBrandButton} bg-accent text-brand`}
          >
            <Play size={18} aria-hidden="true" /> Continue reading
          </button>
          <button
            type="button"
            onClick={() => navigate('/app/reader/new')}
            className={`${onBrandButton} border-white/20 bg-white/10 text-white hover:bg-white/15`}
          >
            <Plus size={18} aria-hidden="true" /> Add a text
          </button>
        </div>
      </div>
      <div className="absolute inset-y-0 right-0 hidden w-[34%] max-w-[330px] sm:block" aria-hidden="true">
        <span className="absolute right-[11%] top-1 h-[73px] w-[73px] rounded-full bg-accent opacity-95" />
        <span className="absolute left-[6%] top-[12%] h-[54px] w-[31px] rotate-[30deg] rounded-[100%_0_100%_0] bg-action" />
        <span className="absolute left-[15%] top-[38%] h-[41px] w-[23px] rotate-[75deg] rounded-[100%_0_100%_0] bg-action" />
      </div>
    </section>
  )
}
