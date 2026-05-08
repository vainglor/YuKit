import { ApiError } from './tools'

export type Base64Mode = 'encode' | 'decode'

export type Base64RunOptions = {
  mode: Base64Mode
  charset: string
}

export type Base64RunPayload = {
  input: { text: string }
  options: Base64RunOptions
}

export type Base64RunResult = {
  execution_id: string
  tool: string
  status: 'succeeded'
  mode: 'sync'
  duration_ms: number
  result: {
    text: string
    size_bytes: number
  }
}

export function buildBase64RunPayload(text: string, options: Base64RunOptions): Base64RunPayload {
  return {
    input: { text },
    options
  }
}

export async function runBase64Codec(
  text: string,
  options: Base64RunOptions,
  apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
): Promise<Base64RunResult> {
  const response = await fetch(`${apiBase.replace(/\/$/, '')}/tools/base64/runs`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildBase64RunPayload(text, options))
  })
  const body = await response.json()

  if (!response.ok) {
    const error = body.error ?? {}
    throw new ApiError(error.message ?? 'Tool run failed', error.code ?? 'tool_run_failed', error.detail)
  }

  return body as Base64RunResult
}
