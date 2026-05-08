import { describe, expect, it } from 'vitest'

import { buildRegexRunPayload } from './regex'

describe('buildRegexRunPayload', () => {
  it('keeps regex text and pattern input separate from execution options', () => {
    expect(
      buildRegexRunPayload('alpha gamma', {
        pattern: String.raw`\b\w{5}\b`,
        flags: ['ignorecase'],
        maxMatches: 10,
        timeoutMs: 50
      })
    ).toEqual({
      input: { text: 'alpha gamma', pattern: String.raw`\b\w{5}\b` },
      options: { flags: ['ignorecase'], max_matches: 10, timeout_ms: 50 }
    })
  })
})
