import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Logo } from '../../components/Logo'
import { CURRENT_USER_QUERY_KEY } from '../../hooks/useCurrentUser'
import { ApiError, extractFieldErrors, registerUser } from '../../lib/api'
import { FormField } from './FormField'
import { PasswordInput } from './PasswordInput'

const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,30}$/
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FormValues {
  username: string
  email: string
  password: string
  confirmPassword: string
}

function validate(values: FormValues): Record<string, string> {
  const errors: Record<string, string> = {}

  if (!USERNAME_PATTERN.test(values.username)) {
    errors.username =
      'Username must be 3-30 characters: letters, digits, underscores, dots, or hyphens.'
  }
  if (!EMAIL_PATTERN.test(values.email)) {
    errors.email = 'Enter a valid email address.'
  }
  if (values.password.length < 8 || values.password.length > 128) {
    errors.password = 'Password must be between 8 and 128 characters.'
  }
  if (values.password !== values.confirmPassword) {
    errors.confirmPassword = 'Passwords must match.'
  }

  return errors
}

export function Signup() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [values, setValues] = useState<FormValues>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: registerUser,
    onSuccess: (user) => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, user)
      navigate('/app')
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && (error.status === 409 || error.status === 422)) {
        setFieldErrors(extractFieldErrors(error.detail))
        return
      }
      setFormError('Something went wrong. Please try again.')
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)

    const clientErrors = validate(values)
    setFieldErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) return

    mutation.mutate({ username: values.username, email: values.email, password: values.password })
  }

  function updateField(field: keyof FormValues) {
    return (event: ChangeEvent<HTMLInputElement>) =>
      setValues((current) => ({ ...current, [field]: event.target.value }))
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-6 py-16">
      <Logo />
      <div className="mt-8 w-full max-w-md rounded-md border border-line bg-white p-8 shadow-card">
        <h1 className="text-2xl tracking-tight">Create your account</h1>
        <p className="mt-1.5 text-sm text-muted">
          Start reading German with context-aware help.
        </p>

        {formError && (
          <p role="alert" className="mt-4 rounded-sm bg-surface-coral px-3.5 py-2.5 text-xs text-[#8a5141]">
            {formError}
          </p>
        )}

        <form className="mt-6 grid gap-4" onSubmit={handleSubmit} noValidate>
          <FormField label="Username" error={fieldErrors.username}>
            <input
              value={values.username}
              onChange={updateField('username')}
              autoComplete="username"
              placeholder="alex_morgan"
              className="h-[43px] w-full rounded-sm border border-line px-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
            />
          </FormField>

          <FormField label="Email" error={fieldErrors.email}>
            <input
              type="email"
              value={values.email}
              onChange={updateField('email')}
              autoComplete="email"
              placeholder="you@example.com"
              className="h-[43px] w-full rounded-sm border border-line px-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
            />
          </FormField>

          <FormField label="Password" hint="At least 8 characters" error={fieldErrors.password}>
            <PasswordInput
              value={values.password}
              onChange={updateField('password')}
              autoComplete="new-password"
            />
          </FormField>

          <FormField label="Confirm password" error={fieldErrors.confirmPassword}>
            <PasswordInput
              value={values.confirmPassword}
              onChange={updateField('confirmPassword')}
              autoComplete="new-password"
            />
          </FormField>

          <Button type="submit" className="mt-2 w-full" disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating account…' : 'Create account'}
          </Button>
        </form>

        <p className="mt-5 text-center text-xs text-muted">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-action">
            Log in
          </Link>
        </p>
      </div>
    </div>
  )
}
