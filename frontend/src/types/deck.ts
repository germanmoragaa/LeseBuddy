// Mirrors the backend's deck schemas exactly (snake_case, matching the JSON the API returns).
export interface Deck {
  id: string
  name: string
  description: string | null
  total_count: number
  due_count: number
  created_at: string
  updated_at: string
}

export interface DeckListResponse {
  items: Deck[]
}

export interface DeckCreatePayload {
  name: string
  description?: string | null
}

export interface DeckUpdatePayload {
  name?: string
  description?: string | null
}
