import { describe, expect, it } from 'vitest'

import { buildPreferencesPayload, isTerminalExecutionStatus } from './platform'

describe('buildPreferencesPayload', () => {
  it('stores JSON formatter options under the tool name', () => {
    const payload = buildPreferencesPayload({ indent: 4, sortKeys: false, ensureAscii: true })

    expect(payload).toEqual({
      tool_options: {
        'json-format': { indent: 4, sortKeys: false, ensureAscii: true }
      },
      ui: {}
    })
  })
})

describe('isTerminalExecutionStatus', () => {
  it('distinguishes pollable async statuses from terminal statuses', () => {
    expect(isTerminalExecutionStatus('queued')).toBe(false)
    expect(isTerminalExecutionStatus('running')).toBe(false)
    expect(isTerminalExecutionStatus('succeeded')).toBe(true)
    expect(isTerminalExecutionStatus('failed')).toBe(true)
    expect(isTerminalExecutionStatus('timed_out')).toBe(true)
    expect(isTerminalExecutionStatus('canceled')).toBe(true)
  })
})
