import { Navigate, Outlet, useLocation } from 'react-router'

import { useCurrentUser } from '../hooks/useCurrentUser'

export function ProtectedRoute() {
  const { data, isPending } = useCurrentUser()
  const location = useLocation()

  if (isPending) {
    return null
  }

  if (!data) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (!data.email_verified) {
    return <Navigate to="/verify-email" state={{ from: location }} replace />
  }

  return <Outlet />
}
