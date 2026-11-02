import type { ReactNode } from 'react'

interface FormFieldProps {
  label: string
  hint?: string
  error?: string
  children: ReactNode
}

export function FormField({ label, hint, error, children }: FormFieldProps) {
  return (
    <label className="block text-left">
      <span className="mb-1.5 flex justify-between text-[10px] font-bold">
        {label}
        {hint && <small className="font-normal text-muted">{hint}</small>}
      </span>
      {children}
      {error && (
        <span role="alert" className="mt-1.5 block text-[10px] font-semibold text-danger">
          {error}
        </span>
      )}
    </label>
  )
}
