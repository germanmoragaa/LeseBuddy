import { QueryClientProvider } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'

function ReaderStub() {
  const { articleId } = useParams()
  return <div>Reader for {articleId}</div>
}

// Test-only harness: renders `ui` at /app with a stub reader route, so a successful save's
// navigate(`/app/reader/:id`) is observable as "Reader for <id>".
export function SongTestApp({ ui, queryClient }: { ui: ReactElement; queryClient: QueryClient }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={ui} />
          <Route path="/app/reader/:articleId" element={<ReaderStub />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}
