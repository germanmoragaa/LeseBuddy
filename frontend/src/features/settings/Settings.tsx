import { useMutation, useQueryClient } from '@tanstack/react-query'

import { Card } from '../../components/Card'
import { CURRENT_USER_QUERY_KEY, useCurrentUser } from '../../hooks/useCurrentUser'
import { patchMe } from '../../lib/api'

const LANGUAGE_OPTIONS = [
  { value: 'EN-US', label: 'English' },
  { value: 'ES', label: 'Spanish' },
]

export function Settings() {
  const queryClient = useQueryClient()
  const { data: currentUser } = useCurrentUser()

  const mutation = useMutation({
    mutationFn: (language: string) => patchMe(language),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(CURRENT_USER_QUERY_KEY, updatedUser)
    },
  })

  return (
    <div>
      <div className="mb-7">
        <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
          Preferences
        </span>
        <h1 className="my-1.5 text-[33px] tracking-tight">Settings</h1>
        <p className="m-0 text-[13px] text-muted">
          Control how LeseBuddy translates words for you.
        </p>
      </div>

      <Card className="max-w-md p-6">
        <span className="mb-1.5 block text-[9px] font-bold uppercase tracking-wide text-muted">
          Translation language
        </span>
        <p className="mb-3 text-[12px] text-muted">
          Contextual word and sentence translations in the reader are shown in this language.
        </p>
        <select
          aria-label="Translation language"
          value={currentUser?.translation_language ?? 'EN-US'}
          onChange={(event) => mutation.mutate(event.target.value)}
          disabled={mutation.isPending}
          className="h-[42px] w-full rounded-sm border border-line bg-white px-2.5 text-xs text-ink"
        >
          {LANGUAGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {mutation.isError && (
          <p className="mt-2 text-[11px] text-danger" role="alert">
            Couldn't save your preference. Please try again.
          </p>
        )}
      </Card>
    </div>
  )
}
