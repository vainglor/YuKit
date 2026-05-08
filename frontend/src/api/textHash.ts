export type TextHashAlgorithm = 'sha256' | 'sha512' | 'md5'

export type TextHashRunOptions = {
  algorithm: TextHashAlgorithm
}

export type TextHashRunPayload = {
  input: { text: string }
  options: TextHashRunOptions
}

export type TextHashRunResult = {
  execution_id: string
  tool: string
  status: 'queued'
  mode: 'async'
}

export function buildTextHashRunPayload(
  text: string,
  options: TextHashRunOptions
): TextHashRunPayload {
  return {
    input: { text },
    options
  }
}

export async function runTextHash(
  text: string,
  options: TextHashRunOptions,
  apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
): Promise<TextHashRunResult> {
  const response = await fetch(`${apiBase.replace(/\/$/, '')}/tools/text-hash/runs`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildTextHashRunPayload(text, options))
  })
  const body = await response.json()

  if (!response.ok) {
    const error = body.error ?? {}
    throw new Error(error.message ?? 'Tool run failed')
  }

  return body as TextHashRunResult
}
