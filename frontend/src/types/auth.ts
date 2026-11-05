// Mirrors the backend's UserMe schema exactly (snake_case, matching the JSON the API returns).
export interface CurrentUser {
  id: string
  username: string
  email: string
  email_verified: boolean
  translation_language: string
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

export interface VerifyEmailPayload {
  code: string
}

export interface FieldError {
  loc: string[]
  msg: string
  type: string
}

// Shape of the `detail` object on verify-email/resend-verification error responses, and on
// any 403 carrying { code: "email_not_verified", ... }.
export interface ApiErrorDetail {
  code: string
  message: string
  retry_after?: number
}
