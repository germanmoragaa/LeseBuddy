import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Logo } from '../../components/Logo'
import { CURRENT_USER_QUERY_KEY } from '../../hooks/useCurrentUser'
import { ApiError, loginUser } from '../../lib/api'
import { FormField } from './FormField'
import { PasswordInput } from './PasswordInput'

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const state = location.state as { from?: { pathname: string } } | null
  const redirectTo = state?.from?.pathname ?? '/app'

  const mutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (user) => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, user)
      navigate(redirectTo, { replace: true })
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 429) {
        setFormError(
          typeof error.detail === 'string'
            ? error.detail
            : 'Too many failed attempts. Please try again later.',
        )
        return
      }
      if (error instanceof ApiError && error.status === 401) {
        setFormError('Incorrect email/username or password.')
        return
      }
      setFormError('Something went wrong. Please try again.')
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    mutation.mutate({ identifier, password })
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-6 py-16">
      <Logo />
      <div className="mt-8 w-full max-w-md rounded-md border border-line bg-white p-8 shadow-card">
        <h1 className="text-2xl tracking-tight">Welcome back</h1>
        <p className="mt-1.5 text-sm text-muted">Log in to keep reading.</p>

        {formError && (
          <p
            role="alert"
            className="mt-4 rounded-sm bg-surface-coral px-3.5 py-2.5 text-xs text-[#8a5141]"
          >
            {formError}
          </p>
        )}

        <form className="mt-6 grid gap-4" onSubmit={handleSubmit} noValidate>
          <FormField label="Email or username">
            <input
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              autoComplete="username"
              placeholder="you@example.com or username"
              className="h-[43px] w-full rounded-sm border border-line px-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
            />
          </FormField>

          <FormField label="Password">
            <PasswordInput
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </FormField>

          <Button type="submit" className="mt-2 w-full" disabled={mutation.isPending}>
            {mutation.isPending ? 'Logging in…' : 'Log in'}
          </Button>
        </form>

        <p className="mt-5 text-center text-xs text-muted">
          New here?{' '}
          <Link to="/signup" className="font-semibold text-action">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
