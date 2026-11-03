import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App.tsx'
import { CURRENT_USER_QUERY_KEY } from './hooks/useCurrentUser'
import './index.css'
import { ApiError, isApiErrorDetail } from './lib/api'

// Route guards (ProtectedRoute, RequireUnverifiedRoute) already prevent reaching gated
// screens in the normal flow — this only covers a stale ['me'] cache going unverified-403
// against a real protected endpoint. Invalidating refetches 'me', and the guard that's
// currently mounted redirects once it sees email_verified: false.
function handleAuthRelatedErrors(error: unknown) {
  if (!(error instanceof ApiError)) return

  if (error.status === 401) {
    queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null)
    return
  }

  if (error.status === 403 && isApiErrorDetail(error.detail) && error.detail.code === 'email_not_verified') {
    queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY })
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: handleAuthRelatedErrors }),
  mutationCache: new MutationCache({ onError: handleAuthRelatedErrors }),
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)
