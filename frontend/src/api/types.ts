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

export type QuestStatus = 'active' | 'completed' | 'failed' | 'archived'

export interface Quest {
  id: number
  name: string
  description: string | null
  tier_id: number
  category_id: number | null
  recurring_quest_id: number | null
  period_date: string | null
  reward: number
  penalty: number
  status: QuestStatus
  created_at: string
  due_at: string | null
  completed_at: string | null
  penalty_applied: boolean
}

export interface QuestPayload {
  name: string
  description: string | null
  tier_id: number
  category_id: number | null
  reward: number
  penalty: number
  due_at: string | null
}

export interface QuestCompleted {
  quest: Quest
  balance: number
}

export type Frequency = 'daily' | 'weekly' | 'monthly'

export interface RecurringQuest {
  id: number
  name: string
  description: string | null
  tier_id: number
  category_id: number | null
  reward: number
  penalty: number
  frequency: Frequency
  interval: number
  /** 1 — понедельник … 7 — воскресенье. */
  days_of_week: number[] | null
  /** 31 — последний день месяца. */
  day_of_month: number | null
  /** «HH:MM:SS», локальное время пользователя. */
  due_time: string
  start_date: string
  end_date: string | null
  is_active: boolean
  is_archived: boolean
  created_at: string
  next_due_at: string | null
}

export type RecurringPayload = Pick<
  RecurringQuest,
  | 'name'
  | 'description'
  | 'tier_id'
  | 'category_id'
  | 'reward'
  | 'penalty'
  | 'frequency'
  | 'interval'
  | 'days_of_week'
  | 'day_of_month'
  | 'due_time'
  | 'start_date'
  | 'end_date'
>

export type TransactionType = 'quest_reward' | 'penalty' | 'purchase' | 'manual'

export interface Transaction {
  id: number
  amount: number
  type: TransactionType
  quest_id: number | null
  reward_id: number | null
  note: string | null
  balance_after: number
  created_at: string
  title: string | null
}

export interface TransactionPage {
  items: Transaction[]
  total: number
}

export interface BalanceChange {
  transaction: Transaction
  balance: number
}

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
