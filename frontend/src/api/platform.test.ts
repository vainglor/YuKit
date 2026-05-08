import { describe, expect, it } from 'vitest'

import { buildPreferencesPayload } from './platform'

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
