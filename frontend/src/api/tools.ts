export type JsonRunOptions = {
  indent: number
  sortKeys: boolean
  ensureAscii: boolean
}

export type JsonRunPayload = {
  input: { text: string }
  options: {
    indent: number
    sort_keys: boolean
    ensure_ascii: boolean
  }
}

export type JsonRunResult = {
  execution_id: string
  tool: string
  status: 'succeeded'
  mode: 'sync'
  duration_ms: number
  result: {
    formatted: string
    valid: boolean
    size_bytes: number
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly detail: unknown = {}
  ) {
    super(message)
  }
}

export function buildJsonRunPayload(text: string, options: JsonRunOptions): JsonRunPayload {
  return {
    input: { text },
    options: {
      indent: options.indent,
      sort_keys: options.sortKeys,
      ensure_ascii: options.ensureAscii
    }
  }
}

export async function runJsonFormat(
  text: string,
  options: JsonRunOptions,
  apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
): Promise<JsonRunResult> {
  const response = await fetch(`${apiBase.replace(/\/$/, '')}/tools/json-format/runs`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildJsonRunPayload(text, options))
  })
  const body = await response.json()

  if (!response.ok) {
    const error = body.error ?? {}
    throw new ApiError(error.message ?? 'Tool run failed', error.code ?? 'tool_run_failed', error.detail)
  }

  return body as JsonRunResult
}
