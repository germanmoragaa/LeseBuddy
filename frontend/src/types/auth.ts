// Mirrors the backend's UserMe schema exactly (snake_case, matching the JSON the API returns).
export interface CurrentUser {
  id: string
  username: string
  email: string
  email_verified: boolean
  created_at: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export interface LoginPayload {
  identifier: string
  password: string
}

export interface FieldError {
  loc: string[]
  msg: string
  type: string
}
