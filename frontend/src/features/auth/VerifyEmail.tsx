import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Logo } from '../../components/Logo'
import { CURRENT_USER_QUERY_KEY, useCurrentUser } from '../../hooks/useCurrentUser'
import {
  ApiError,
  isApiErrorDetail,
  logoutUser,
  resendVerification,
  verifyEmail,
} from '../../lib/api'
import { FormField } from './FormField'

// Matches the backend's default cooldown (app/core/config.py: verification_resend_cooldown_seconds).
// Only used to seed the initial countdown right after signup; a real remaining-time value for
// cooldowns hit later comes from the 429's retry_after.
const INITIAL_RESEND_COOLDOWN_SECONDS = 60

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && isApiErrorDetail(error.detail)) {
    return error.detail.message
  }
  return fallback
}

function retryAfterSeconds(error: unknown): number | null {
  if (error instanceof ApiError && isApiErrorDetail(error.detail)) {
    return typeof error.detail.retry_after === 'number' ? error.detail.retry_after : null
  }
  return null
}

export function VerifyEmail() {
  const { data: user } = useCurrentUser()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(INITIAL_RESEND_COOLDOWN_SECONDS)

  useEffect(() => {
    if (secondsLeft <= 0) return
    const timer = setInterval(() => {
      setSecondsLeft((current) => Math.max(0, current - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [secondsLeft])

  const verifyMutation = useMutation({
    mutationFn: verifyEmail,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, updatedUser)
      const state = location.state as { from?: { pathname: string } } | null
      navigate(state?.from?.pathname ?? '/app', { replace: true })
    },
    onError: (error: unknown) => {
      setFormError(errorMessage(error, 'Something went wrong. Please try again.'))
    },
  })

  const resendMutation = useMutation({
    mutationFn: resendVerification,
    onSuccess: () => {
      setFormError(null)
      setSecondsLeft(INITIAL_RESEND_COOLDOWN_SECONDS)
    },
    onError: (error: unknown) => {
      const retryAfter = retryAfterSeconds(error)
      if (retryAfter !== null) {
        setSecondsLeft(retryAfter)
        setFormError('Please wait before requesting another code.')
        return
      }
      setFormError(errorMessage(error, 'Something went wrong. Please try again.'))
    },
  })

  const logoutMutation = useMutation({
    mutationFn: logoutUser,
    onSuccess: () => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null)
      navigate('/login', { replace: true })
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    verifyMutation.mutate({ code })
  }

  function handleCodeChange(event: ChangeEvent<HTMLInputElement>) {
    setCode(event.target.value.replace(/\D/g, '').slice(0, 6))
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-6 py-16">
      <Logo />
      <div className="mt-8 w-full max-w-md rounded-md border border-line bg-white p-8 shadow-card">
        <h1 className="text-2xl tracking-tight">Verify your email</h1>
        <p className="mt-1.5 text-sm text-muted">
          We sent a 6-digit code to{' '}
          <span className="font-semibold text-ink">{user?.email}</span>. Enter it below to
          continue.
        </p>

        {formError && (
          <p
            role="alert"
            className="mt-4 rounded-sm bg-surface-coral px-3.5 py-2.5 text-xs text-[#8a5141]"
          >
            {formError}
          </p>
        )}

        <form className="mt-6 grid gap-4" onSubmit={handleSubmit} noValidate>
          <FormField label="Verification code">
            <input
              value={code}
              onChange={handleCodeChange}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="123456"
              className="h-[43px] w-full rounded-sm border border-line px-3.5 text-center text-lg tracking-[0.4em] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
            />
          </FormField>

          <Button
            type="submit"
            className="w-full"
            disabled={verifyMutation.isPending || code.length !== 6}
          >
            {verifyMutation.isPending ? 'Verifying…' : 'Verify email'}
          </Button>
        </form>

        <div className="mt-5 flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={() => resendMutation.mutate()}
            disabled={secondsLeft > 0 || resendMutation.isPending}
            className="font-semibold text-action disabled:cursor-not-allowed disabled:text-muted"
          >
            {secondsLeft > 0 ? `Resend code (${secondsLeft}s)` : 'Resend code'}
          </button>
          <button
            type="button"
            onClick={() => logoutMutation.mutate()}
            className="text-muted hover:text-ink"
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  )
}
