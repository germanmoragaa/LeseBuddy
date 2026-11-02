import { Link } from 'react-router'

import { Logo } from '../../components/Logo'

const linkBase =
  'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-sm border border-transparent px-5 text-[13px] font-bold transition hover:-translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action'
const primaryLink = `${linkBase} bg-brand text-white shadow-[0_5px_16px_rgb(36_76_59_/_0.15)] hover:bg-brand-dark`
const secondaryLink = `${linkBase} border-line bg-white text-ink hover:border-[#cfd5cd] hover:bg-[#fdfdfa]`

export function Welcome() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-6 py-16 text-center">
      <Logo />
      <h1 className="mt-10 max-w-xl text-2xl font-semibold leading-snug tracking-tight text-ink sm:text-3xl">
        Read authentic German. Understand more. Remember what you learn.
      </h1>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-muted">
        Paste a German text, get contextual explanations for the words and expressions you
        select, and turn them into flashcards you'll actually remember — all in one reading
        companion.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link to="/signup" className={primaryLink}>
          Create account
        </Link>
        <Link to="/login" className={secondaryLink}>
          Log in
        </Link>
      </div>
    </div>
  )
}
