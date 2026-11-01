import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'icon'

const base =
  'inline-flex min-h-[42px] items-center justify-center gap-2 rounded-sm border border-transparent px-4 text-[13px] font-bold transition hover:-translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:pointer-events-none disabled:opacity-50'

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-brand text-white shadow-[0_5px_16px_rgb(36_76_59_/_0.15)] hover:bg-brand-dark',
  secondary: 'border-line bg-white text-ink hover:border-[#cfd5cd] hover:bg-[#fdfdfa]',
  ghost: 'text-muted hover:bg-black/5',
  icon: 'min-h-10 w-10 border-line bg-white px-0 text-muted hover:bg-[#fdfdfa]',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  children?: ReactNode
}

export function Button({ variant = 'primary', className = '', children, ...props }: ButtonProps) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}
