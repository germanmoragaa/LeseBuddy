import { useQuery } from '@tanstack/react-query'

import { getHealth } from '../lib/api'

export function ApiStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  })

  if (isPending) {
    return <p className="text-sm text-gray-500">Checking API status…</p>
  }

  if (isError) {
    return <p className="text-sm text-red-600">API status: error</p>
  }

  return <p className="text-sm text-green-600">API status: {data.status}</p>
}
