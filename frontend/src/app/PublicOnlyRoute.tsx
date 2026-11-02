import { Navigate, Outlet } from 'react-router'

import { useCurrentUser } from '../hooks/useCurrentUser'

export function PublicOnlyRoute() {
  const { data, isPending } = useCurrentUser()

  if (isPending) {
    return null
  }

  if (data) {
    return <Navigate to="/app" replace />
  }

  return <Outlet />
}
