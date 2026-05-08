import { ApiError } from './tools'

export type TimestampMode = 'from-unix' | 'from-iso'

export type TimestampRunOptions = {
  mode: TimestampMode
}

export type TimestampRunPayload = {
  input: { text: string }
  options: TimestampRunOptions
}

export type TimestampRunResult = {
  execution_id: string
  tool: string
  status: 'succeeded'
  mode: 'sync'
  duration_ms: number
  result: {
    unix_seconds: number
    unix_milliseconds: number
    iso_utc: string
  }
}

export function buildTimestampRunPayload(
  text: string,
  options: TimestampRunOptions
): TimestampRunPayload {
  return {
    input: { text },
    options
  }
}

export async function runTimestampConverter(
  text: string,
  options: TimestampRunOptions,
  apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
): Promise<TimestampRunResult> {
  const response = await fetch(`${apiBase.replace(/\/$/, '')}/tools/timestamp/runs`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildTimestampRunPayload(text, options))
  })
  const body = await response.json()

  if (!response.ok) {
    const error = body.error ?? {}
    throw new ApiError(error.message ?? 'Tool run failed', error.code ?? 'tool_run_failed', error.detail)
  }

  return body as TimestampRunResult
}
