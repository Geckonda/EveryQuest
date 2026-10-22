import { describe, expect, it } from 'vitest'
import { ApiError } from '../client'
import { archiveConflictOf, errorMessage, tierInUseOf } from '../errors'

const conflict = {
  message: 'Сначала завершите квесты',
  quests: [{ id: 1, name: 'Пробежка' }],
  recurring_quests: [],
}

describe('archiveConflictOf', () => {
  it('распознаёт 409 со списком квестов', () => {
    const error = new ApiError(409, { detail: conflict })
    expect(archiveConflictOf(error)).toEqual(conflict)
    expect(error.message).toBe('Сначала завершите квесты')
  })

  it('игнорирует другие ошибки', () => {
    expect(archiveConflictOf(new ApiError(409, { detail: 'Email занят' }))).toBeNull()
    expect(archiveConflictOf(new ApiError(400, { detail: conflict }))).toBeNull()
    expect(archiveConflictOf(new TypeError('network'))).toBeNull()
  })
})

describe('errorMessage', () => {
  it('сетевая ошибка — общее сообщение', () => {
    expect(errorMessage(new TypeError('Failed to fetch'))).toBe('Не удалось связаться с сервером')
  })
})

describe('tierInUseOf', () => {
  it('распознаёт 409 «тир используется» с числом квестов', () => {
    const usage = { message: 'Тир используется', quests: 3, recurring_quests: 1 }
    expect(tierInUseOf(new ApiError(409, { detail: usage }))).toEqual(usage)
  })

  it('не путает с архивным конфликтом и другими ошибками', () => {
    expect(tierInUseOf(new ApiError(409, { detail: conflict }))).toBeNull()
    expect(tierInUseOf(new ApiError(409, { detail: 'Это последний тир' }))).toBeNull()
    expect(tierInUseOf(new TypeError('network'))).toBeNull()
  })
})
