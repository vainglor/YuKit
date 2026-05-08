import { describe, expect, it } from 'vitest'

import { buildTextHashRunPayload } from './textHash'

describe('buildTextHashRunPayload', () => {
  it('keeps raw text input separate from hash options', () => {
    expect(buildTextHashRunPayload('YuKit', { algorithm: 'sha256' })).toEqual({
      input: { text: 'YuKit' },
      options: { algorithm: 'sha256' }
    })
  })
})
