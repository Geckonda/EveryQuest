export const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(extractMessage(status, body))
  }
}

/**
 * FastAPI отдаёт detail строкой (HTTPException), списком ошибок валидации (422)
 * или объектом с полем message (например, 409 при архивации).
 */
function extractMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') return detail[0].msg
  const message = (detail as { message?: unknown } | null)?.message
  if (typeof message === 'string') return message
  return `Ошибка сервера (${status})`
}

export interface AuthHandler {
  getAccessToken(): string | null
  /** Пытается обновить access-токен; true — можно повторить запрос. */
  refresh(): Promise<boolean>
  onUnauthorized(): void
}

let authHandler: AuthHandler | null = null

export function setAuthHandler(handler: AuthHandler | null): void {
  authHandler = handler
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response = await send(method, path, body)

  if (response.status === 401 && authHandler?.getAccessToken()) {
    if (await authHandler.refresh()) {
      response = await send(method, path, body)
    }
    if (response.status === 401) authHandler.onUnauthorized()
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data)
  return data as T
}

function send(method: string, path: string, body: unknown): Promise<Response> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = authHandler?.getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(`${API_PREFIX}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
}
