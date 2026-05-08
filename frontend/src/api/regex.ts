import { ApiError } from './tools'

export type RegexFlag = 'ignorecase' | 'multiline' | 'dotall' | 'ascii' | 'verbose'

export type RegexRunOptions = {
  pattern: string
  flags: RegexFlag[]
  maxMatches: number
  timeoutMs: number
}

export type RegexRunPayload = {
  input: { text: string; pattern: string }
  options: {
    flags: RegexFlag[]
    max_matches: number
    timeout_ms: number
  }
}

export type RegexRunResult = {
  execution_id: string
  tool: string
  status: 'succeeded'
  mode: 'sync'
  duration_ms: number
  result: {
    matches: Array<{
      text: string
      start: number
      end: number
      groups: Array<string | null>
      named_groups: Record<string, string | null>
    }>
    count: number
    truncated: boolean
  }
}

export function buildRegexRunPayload(text: string, options: RegexRunOptions): RegexRunPayload {
  return {
    input: { text, pattern: options.pattern },
    options: {
      flags: options.flags,
      max_matches: options.maxMatches,
      timeout_ms: options.timeoutMs
    }
  }
}

export async function runRegexTest(
  text: string,
  options: RegexRunOptions,
  apiBase = import.meta.env.VITE_API_BASE_URL ?? '/api'
): Promise<RegexRunResult> {
  const response = await fetch(`${apiBase.replace(/\/$/, '')}/tools/regex-test/runs`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildRegexRunPayload(text, options))
  })
  const body = await response.json()

  if (!response.ok) {
    const error = body.error ?? {}
    throw new ApiError(error.message ?? 'Tool run failed', error.code ?? 'tool_run_failed', error.detail)
  }

  return body as RegexRunResult
}
