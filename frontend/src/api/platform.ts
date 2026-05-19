import { normalizeAuthOptions, type AuthOptions } from '../authFlow'

export type { AuthOptions } from '../authFlow'

export type UserProfile = {
  id: string
  email: string
  display_name: string
  avatar_url: string
  created_at: string
  updated_at: string
  identities: AccountIdentity[]
}

export type AccountIdentity = {
  provider: string
  provider_email: string
  created_at: string
}

export type AccountSession = {
  id: string
  created_at: string
  updated_at: string
  expires_at: string
  revoked_at: string | null
  is_current: boolean
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

export type ExecutionDetail = {
  id: string
  tool: string
  status: string
  mode: string
  duration_ms: number | null
  result: unknown
  error_code: string
  error_message: string
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

export function isTerminalExecutionStatus(status: string): boolean {
  return ['succeeded', 'failed', 'timed_out', 'canceled'].includes(status)
}

export async function fetchMe(): Promise<UserProfile | null> {
  const body = await request<{ user: UserProfile | null }>('/auth/me')
  return body.user
}

export async function fetchAuthOptions(): Promise<AuthOptions> {
  const body = await request<AuthOptions>('/auth/options')
  return normalizeAuthOptions(body)
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

export async function updateProfile(profile: {
  display_name: string
  avatar_url: string
}): Promise<UserProfile> {
  const body = await request<{ user: UserProfile }>('/me/profile', {
    method: 'PUT',
    body: JSON.stringify(profile)
  })
  return body.user
}

export async function fetchSessions(): Promise<AccountSession[]> {
  const body = await request<{ sessions: AccountSession[] }>('/me/sessions')
  return body.sessions
}

export async function revokeOtherSessions(): Promise<AccountSession[]> {
  const body = await request<{ sessions: AccountSession[] }>('/me/sessions/revoke-others', {
    method: 'POST'
  })
  return body.sessions
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

export async function fetchExecution(executionId: string): Promise<ExecutionDetail> {
  const body = await request<{ execution: ExecutionDetail }>(`/executions/${executionId}`)
  return body.execution
}

export async function cancelExecution(executionId: string): Promise<ExecutionDetail> {
  const body = await request<{ execution: ExecutionDetail }>(`/executions/${executionId}/cancel`, {
    method: 'POST'
  })
  return body.execution
}
