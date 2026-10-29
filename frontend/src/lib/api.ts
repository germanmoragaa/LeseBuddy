const API_BASE_PATH = '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_PATH}${path}`)

  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status)
  }

  return response.json() as Promise<T>
}

export interface HealthResponse {
  status: string
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}
