// Mirrors the backend's ArticleListItem/ArticleRead schemas (snake_case, matching the JSON
// the API returns).
export interface ArticleListItem {
  id: string
  title: string | null
  source_url: string | null
  language: string
  created_at: string
  updated_at: string
  word_count: number
  excerpt: string | null
}

export interface Article extends ArticleListItem {
  original_text: string
}

export interface ArticleCreatePayload {
  title?: string
  source_url?: string
  original_text: string
  language?: string
}

export interface ArticleUpdatePayload {
  title: string
}

export interface ArticleListResponse {
  items: ArticleListItem[]
  total: number
  page: number
  page_size: number
}
