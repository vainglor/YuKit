import { describe, expect, it } from 'vitest'

import { buildTimestampRunPayload } from './timestamp'

describe('buildTimestampRunPayload', () => {
  it('keeps timestamp input separate from conversion options', () => {
    expect(
      buildTimestampRunPayload('1700000000', {
        mode: 'from-unix'
      })
    ).toEqual({
      input: { text: '1700000000' },
      options: { mode: 'from-unix' }
    })
  })
})
