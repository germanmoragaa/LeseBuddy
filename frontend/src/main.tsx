import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App.tsx'
import { CURRENT_USER_QUERY_KEY } from './hooks/useCurrentUser'
import './index.css'
import { ApiError } from './lib/api'

function clearCurrentUserOn401(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null)
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: clearCurrentUserOn401 }),
  mutationCache: new MutationCache({ onError: clearCurrentUserOn401 }),
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
