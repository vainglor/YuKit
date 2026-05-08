import { describe, expect, it } from 'vitest'

import { buildJsonRunPayload } from './tools'

describe('buildJsonRunPayload', () => {
  it('keeps raw JSON input separate from formatting options', () => {
    expect(
      buildJsonRunPayload('{"b":1,"a":2}', {
        indent: 2,
        sortKeys: true,
        ensureAscii: false
      })
    ).toEqual({
      input: { text: '{"b":1,"a":2}' },
      options: { indent: 2, sort_keys: true, ensure_ascii: false }
    })
  })
})
