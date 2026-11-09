import type { ArticleAnalysis } from '../types/analysis'
import type {
  Article,
  ArticleCreatePayload,
  ArticleListResponse,
  ArticleUpdatePayload,
} from '../types/article'
import type {
  ApiErrorDetail,
  CurrentUser,
  LoginPayload,
  RegisterPayload,
  VerifyEmailPayload,
} from '../types/auth'
import type { DictionaryLookupResult } from '../types/dictionary'
import type {
  DueFlashcardsResponse,
  ReviewSubmitPayload,
  ReviewSubmitResult,
  ReviewSummary,
} from '../types/flashcards'
import type { TranslatePayload, TranslateResult } from '../types/translation'
import type {
  VocabularyItem,
  VocabularyItemDetail,
  VocabularyListResponse,
  VocabularyOccurrenceSummary,
  VocabularyPatchPayload,
  VocabularySaveResponse,
} from '../types/vocabulary'

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

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
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

export function patchMe(translationLanguage: string): Promise<CurrentUser> {
  return apiPatch<CurrentUser>('/me', { translation_language: translationLanguage })
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

export function verifyEmail(payload: VerifyEmailPayload): Promise<CurrentUser> {
  return apiPost<CurrentUser>('/auth/verify-email', payload)
}

export function resendVerification(): Promise<void> {
  return apiPost<void>('/auth/resend-verification', {})
}

// Both verify-email and resend-verification (and any future "email_not_verified" 403) return
// detail as {code, message} (resend's 429 also carries retry_after), never the field-error list.
export function isApiErrorDetail(detail: unknown): detail is ApiErrorDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    'code' in detail &&
    typeof (detail as { code: unknown }).code === 'string'
  )
}

export function createArticle(payload: ArticleCreatePayload): Promise<Article> {
  return apiPost<Article>('/articles', payload)
}

export interface ListArticlesParams {
  page?: number
  pageSize?: number
}

// Runtime guard against a backend still serving the pre-pagination, bare-array response —
// without this, `data?.items ?? []` would silently read an unexpected shape as "no articles"
// instead of surfacing an error, hiding real data behind a misleading empty state.
function assertArticleListResponse(data: unknown): ArticleListResponse {
  if (
    typeof data !== 'object' ||
    data === null ||
    !Array.isArray((data as { items?: unknown }).items)
  ) {
    throw new ApiError('Unexpected response shape for GET /articles', 0, data)
  }
  return data as ArticleListResponse
}

export async function listArticles(params: ListArticlesParams = {}): Promise<ArticleListResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.pageSize) query.set('page_size', String(params.pageSize))
  const queryString = query.toString()
  const data = await apiFetch<unknown>(`/articles${queryString ? `?${queryString}` : ''}`)
  return assertArticleListResponse(data)
}

export function getArticle(articleId: string): Promise<Article> {
  return apiFetch<Article>(`/articles/${articleId}`)
}

export function getArticleAnalysis(articleId: string): Promise<ArticleAnalysis> {
  return apiFetch<ArticleAnalysis>(`/articles/${articleId}/analysis`)
}

export function updateArticle(
  articleId: string,
  payload: ArticleUpdatePayload,
): Promise<Article> {
  return apiPatch<Article>(`/articles/${articleId}`, payload)
}

export function deleteArticle(articleId: string): Promise<void> {
  return apiDelete<void>(`/articles/${articleId}`)
}

export function getDictionaryEntry(
  articleId: string,
  start: number,
  end: number,
): Promise<DictionaryLookupResult> {
  return apiFetch<DictionaryLookupResult>(
    `/articles/${articleId}/dictionary?start=${start}&end=${end}`,
  )
}

export function translateSelection(
  articleId: string,
  payload: TranslatePayload,
): Promise<TranslateResult> {
  return apiPost<TranslateResult>(`/articles/${articleId}/translate`, payload)
}

export function getVocabularyOccurrences(
  articleId: string,
): Promise<VocabularyOccurrenceSummary[]> {
  return apiFetch<VocabularyOccurrenceSummary[]>(`/articles/${articleId}/vocabulary-occurrences`)
}

export function saveVocabularyItem(
  articleId: string,
  start: number,
  end: number,
): Promise<VocabularySaveResponse> {
  return apiPost<VocabularySaveResponse>('/vocabulary', { article_id: articleId, start, end })
}

export interface ListVocabularyParams {
  search?: string
  pos?: string
  page?: number
  pageSize?: number
}

export function listVocabulary(params: ListVocabularyParams = {}): Promise<VocabularyListResponse> {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  if (params.pos) query.set('pos', params.pos)
  if (params.page) query.set('page', String(params.page))
  if (params.pageSize) query.set('page_size', String(params.pageSize))
  const queryString = query.toString()
  return apiFetch<VocabularyListResponse>(`/vocabulary${queryString ? `?${queryString}` : ''}`)
}

export function getVocabularyItem(itemId: string): Promise<VocabularyItemDetail> {
  return apiFetch<VocabularyItemDetail>(`/vocabulary/${itemId}`)
}

export function patchVocabularyItem(
  itemId: string,
  payload: VocabularyPatchPayload,
): Promise<VocabularyItem> {
  return apiPatch<VocabularyItem>(`/vocabulary/${itemId}`, payload)
}

export function deleteVocabularyItem(itemId: string): Promise<void> {
  return apiDelete<void>(`/vocabulary/${itemId}`)
}

export function getDueCards(limit = 20): Promise<DueFlashcardsResponse> {
  return apiFetch<DueFlashcardsResponse>(`/reviews/due?limit=${limit}`)
}

export function getReviewSummary(): Promise<ReviewSummary> {
  return apiFetch<ReviewSummary>('/reviews/summary')
}

export function submitReview(payload: ReviewSubmitPayload): Promise<ReviewSubmitResult> {
  return apiPost<ReviewSubmitResult>('/reviews', payload)
}
