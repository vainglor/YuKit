export type UserProfile = {
  id: string
  email: string
  display_name: string
  avatar_url: string
}

export type Preferences = {
  tool_options: Record<string, unknown>
  ui: Record<string, unknown>
}

export type ExecutionSummary = {
  id: string
  tool: string
  status: string
  mode: string
  duration_ms: number | null
  created_at: string
  error_code: string
  error_message: string
  result: unknown
}

export function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init
  })
  const body = await response.json()
  if (!response.ok) {
    const error = body.error ?? {}
    throw new Error(error.message ?? 'Request failed')
  }
  return body as T
}

export function buildPreferencesPayload(options: {
  indent: number
  sortKeys: boolean
  ensureAscii: boolean
}): Preferences {
  return {
    tool_options: {
      'json-format': options
    },
    ui: {}
  }
}

export async function fetchMe(): Promise<UserProfile | null> {
  const body = await request<{ user: UserProfile | null }>('/auth/me')
  return body.user
}

export async function devLogin(): Promise<UserProfile> {
  const body = await request<{ user: UserProfile }>('/auth/dev-login', {
    method: 'POST',
    body: JSON.stringify({ email: 'local@yukit.dev', name: 'Local User' })
  })
  return body.user
}

export async function logout(): Promise<void> {
  await request('/auth/logout', { method: 'POST' })
}

export async function fetchFavorites(): Promise<string[]> {
  const body = await request<{ favorites: string[] }>('/me/favorites')
  return body.favorites
}

export async function setFavorite(tool: string, favorite: boolean): Promise<string[]> {
  const body = await request<{ favorites: string[] }>(`/me/favorites/${tool}`, {
    method: favorite ? 'PUT' : 'DELETE'
  })
  return body.favorites
}

export async function fetchPreferences(): Promise<Preferences> {
  const body = await request<{ preferences: Preferences }>('/me/preferences')
  return body.preferences
}

export async function savePreferences(preferences: Preferences): Promise<Preferences> {
  const body = await request<{ preferences: Preferences }>('/me/preferences', {
    method: 'PUT',
    body: JSON.stringify(preferences)
  })
  return body.preferences
}

export async function fetchExecutions(): Promise<ExecutionSummary[]> {
  const body = await request<{ executions: ExecutionSummary[] }>('/me/executions')
  return body.executions
}
