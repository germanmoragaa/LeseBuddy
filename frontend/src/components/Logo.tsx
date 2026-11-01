export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="grid h-9 w-9 place-items-center rounded-[10px_10px_13px_10px] bg-brand text-white"
        aria-hidden="true"
      >
        <svg viewBox="0 0 34 34" width={27} fill="none" stroke="currentColor" strokeWidth={1.8}>
          <path d="M7 8.5c4.3-.6 7.7.4 10 3v14c-2.3-2.5-5.7-3.5-10-3V8.5Z" />
          <path d="M27 8.5c-4.3-.6-7.7.4-10 3v14c2.3-2.5 5.7-3.5 10-3V8.5Z" />
          <path d="m21.5 5.5 3 3-3 3" />
        </svg>
      </span>
      <span className="text-[19px] font-bold tracking-tight">
        Lese<span className="text-action">Buddy</span>
      </span>
    </div>
  )
}
