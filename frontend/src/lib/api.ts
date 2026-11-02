import type { CurrentUser, LoginPayload, RegisterPayload } from '../types/auth'

const API_BASE_PATH = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_PATH}${path}`, {
    credentials: 'include',
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  })

  if (!response.ok) {
    let detail: unknown
    try {
      detail = (await response.json()).detail
    } catch {
      detail = undefined
    }
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}`,
      response.status,
      detail,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function apiFetch<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

// Turns FastAPI's {"detail": [{"loc": [...], "msg": "..."}]} shape (used by both Pydantic's
// 422s and this app's field-specific 409s) into a {fieldName: message} map components can
// read directly.
export function extractFieldErrors(detail: unknown): Record<string, string> {
  if (!Array.isArray(detail)) return {}

  const errors: Record<string, string> = {}
  for (const item of detail) {
    if (item && typeof item === 'object' && 'loc' in item && 'msg' in item) {
      const loc = item.loc
      const field = Array.isArray(loc) ? loc[loc.length - 1] : undefined
      if (typeof field === 'string') {
        errors[field] = String(item.msg)
      }
    }
  }
  return errors
}

export interface HealthResponse {
  status: string
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}

export function getMe(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>('/me')
}

export function registerUser(payload: RegisterPayload): Promise<CurrentUser> {
  return apiPost<CurrentUser>('/auth/register', payload)
}

export function loginUser(payload: LoginPayload): Promise<CurrentUser> {
  return apiPost<CurrentUser>('/auth/login', payload)
}

export function logoutUser(): Promise<void> {
  return apiPost<void>('/auth/logout', {})
}
