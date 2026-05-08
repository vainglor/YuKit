import { describe, expect, it } from 'vitest'

import { buildBase64RunPayload } from './base64'

describe('buildBase64RunPayload', () => {
  it('keeps raw text input separate from codec options', () => {
    expect(
      buildBase64RunPayload('Hello, YuKit', {
        mode: 'encode',
        charset: 'utf-8'
      })
    ).toEqual({
      input: { text: 'Hello, YuKit' },
      options: { mode: 'encode', charset: 'utf-8' }
    })
  })
})
