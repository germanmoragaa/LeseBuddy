import { Navigate, Outlet } from 'react-router'

import { useCurrentUser } from '../hooks/useCurrentUser'

export function RequireUnverifiedRoute() {
  const { data, isPending } = useCurrentUser()

  if (isPending) {
    return null
  }

  if (!data) {
    return <Navigate to="/login" replace />
  }

  if (data.email_verified) {
    return <Navigate to="/app" replace />
  }

  return <Outlet />
}
