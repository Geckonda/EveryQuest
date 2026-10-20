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

export interface Category {
  id: number
  name: string
  description: string | null
  color: string | null
  is_archived: boolean
}
