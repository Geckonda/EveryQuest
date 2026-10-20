export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: number
  email: string
  username: string
  balance: number
  timezone: string
  created_at: string
}

export interface RegisterPayload {
  email: string
  username: string
  password: string
  timezone: string
}

export interface Tier {
  id: number
  name: string
  level: number
  default_reward: number
  default_penalty: number
  color: string | null
  is_archived: boolean
}

export type TierPayload = Omit<Tier, 'id' | 'is_archived'>

export interface Category {
  id: number
  name: string
  description: string | null
  color: string | null
  is_archived: boolean
}

export type CategoryPayload = Omit<Category, 'id' | 'is_archived'>

export interface Reward {
  id: number
  name: string
  description: string | null
  price: number
  duration_minutes: number | null
  is_archived: boolean
  created_at: string
}

export type RewardPayload = Omit<Reward, 'id' | 'is_archived' | 'created_at'>

export interface ArchiveBlocker {
  id: number
  name: string
}

/** detail ответа 409 при архивации тира или категории. */
export interface ArchiveConflict {
  message: string
  quests: ArchiveBlocker[]
  recurring_quests: ArchiveBlocker[]
}
