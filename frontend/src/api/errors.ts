import { ApiError } from './client'
import type { ArchiveConflict, TierInUse } from './types'

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Не удалось связаться с сервером'
}

/** Если ошибка — 409 «архивировать нельзя», возвращает список мешающих квестов. */
export function archiveConflictOf(error: unknown): ArchiveConflict | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null
  const detail = (error.body as { detail?: unknown } | null)?.detail as ArchiveConflict | undefined
  if (!detail || !Array.isArray(detail.quests) || !Array.isArray(detail.recurring_quests)) {
    return null
  }
  return detail
}

/** Если ошибка — 409 «тир используется», возвращает, сколько квестов и шаблонов переносить. */
export function tierInUseOf(error: unknown): TierInUse | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null
  const detail = (error.body as { detail?: unknown } | null)?.detail as TierInUse | undefined
  if (!detail || typeof detail.quests !== 'number' || typeof detail.recurring_quests !== 'number') {
    return null
  }
  return detail
}
